"""
Utility functions for the X402 CRE Gateway
"""

import os
import json
import time
import uuid
import hashlib
import base64
import logging
from typing import Any, Dict, Tuple
import requests
from eth_account import Account
from eth_account.messages import encode_defunct
from google.cloud import secretmanager

logger = logging.getLogger(__name__)


# ============================================================================
# Google Secret Manager
# ============================================================================

def get_secret(secret_name: str, project_id: str) -> str:
    """
    Fetch a secret from Google Secret Manager
    
    Args:
        secret_name: Name of the secret
        project_id: GCP project ID
    
    Returns:
        Secret value as string
    """
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode('UTF-8')
    except Exception as e:
        logger.error(f"Failed to fetch secret {secret_name}: {str(e)}")
        raise


# ============================================================================
# Utility Functions
# ============================================================================

def sha256(data: Any) -> str:
    """Compute SHA256 hash of data with deterministic JSON serialization"""
    if isinstance(data, str):
        json_string = data
    else:
        # Use sort_keys=True to match json-stable-stringify behavior in TypeScript
        json_string = json.dumps(data, separators=(',', ':'), sort_keys=True)
    
    return hashlib.sha256(json_string.encode('utf-8')).hexdigest()


def base64url_encode(data: bytes) -> str:
    """Encode bytes to base64url format (without padding)"""
    encoded = base64.b64encode(data)
    # Convert to base64url format
    return encoded.decode('ascii').replace('+', '-').replace('/', '_').replace('=', '')


# ============================================================================
# JWT Creation
# ============================================================================

def create_jwt(request: Dict[str, Any], private_key: str) -> str:
    """
    Create a JWT token signed with Ethereum private key
    
    Args:
        request: The JSON-RPC request dictionary
        private_key: Ethereum private key (with 0x prefix)
    
    Returns:
        JWT token string
    """
    # Create account from private key
    account = Account.from_key(private_key)
    address = account.address
    
    # Create JWT header
    header = {
        "alg": "ETH",
        "typ": "JWT"
    }
    
    # Create JWT payload with request and metadata
    now = int(time.time())
    
    payload = {
        "digest": f"0x{sha256(request)}",
        "iss": address,
        "iat": now,
        "exp": now + 300,  # 5 minutes expiration
        "jti": str(uuid.uuid4())
    }
    
    # Encode header and payload - match TypeScript implementation
    header_json = json.dumps(header, separators=(',', ':'))
    payload_json = json.dumps(payload, separators=(',', ':'))
    
    # Base64 encode, then convert to base64url format
    header_b64 = base64.b64encode(header_json.encode('utf-8')).decode('ascii')
    payload_b64 = base64.b64encode(payload_json.encode('utf-8')).decode('ascii')
    
    # Convert to base64url (remove padding, replace chars)
    encoded_header = header_b64.replace('+', '-').replace('/', '_').replace('=', '')
    encoded_payload = payload_b64.replace('+', '-').replace('/', '_').replace('=', '')
    raw_message = f"{encoded_header}.{encoded_payload}"
    
    # Sign the message using Ethereum signing
    message = encode_defunct(text=raw_message)
    signed_message = account.sign_message(message)
    
    # Extract signature components
    signature_bytes = signed_message.signature
    
    # Get v value (recovery id)
    v = signed_message.v
    # Adjust v to be 0 or 1 (instead of 27 or 28)
    recovery_id = v - 27 if v >= 27 else v
    
    # Extract r and s as hex strings and ensure they're padded to 64 hex chars (32 bytes)
    r_hex = signature_bytes[:32].hex().zfill(64)
    s_hex = signature_bytes[32:64].hex().zfill(64)
    
    # Combine r, s, and recovery_id into signature bytes
    r_buffer = bytes.fromhex(r_hex)
    s_buffer = bytes.fromhex(s_hex)
    final_signature = r_buffer + s_buffer + bytes([recovery_id])
    
    # Encode signature to base64url
    signature_b64 = base64.b64encode(final_signature).decode('ascii')
    encoded_signature = signature_b64.replace('+', '-').replace('/', '_').replace('=', '')
    
    return f"{raw_message}.{encoded_signature}"


# ============================================================================
# Core Workflow Trigger Logic
# ============================================================================

def execute_workflow_trigger(input_data: Any) -> Tuple[bool, Dict[str, Any], str]:
    """
    Core logic to trigger a CRE workflow
    
    Args:
        input_data: WorkflowInput with recipient and messages array
    
    Returns:
        Tuple of (success, response_data, request_id)
        - success: True if workflow triggered successfully, False otherwise
        - response_data: Gateway response or error details
        - request_id: UUID of the request
    """
    request_id = str(uuid.uuid4())
    
    try:
        # Get workflow_id and gateway_url from environment
        workflow_id = os.environ.get('WORKFLOW_ID')
        gateway_url = os.environ.get('GATEWAY_URL')
        
        if not workflow_id:
            return False, {"error": "WORKFLOW_ID environment variable not set"}, request_id
        
        if not gateway_url:
            return False, {"error": "GATEWAY_URL environment variable not set"}, request_id
        
        # Get private key - check .env first (for local testing), then Secret Manager
        private_key = os.environ.get('HTTP_TRIGGER_PRIVATE_KEY')
        
        if private_key:
            logger.info("Using private key from environment variable (local mode)")
        else:
            # Fetch from Google Secret Manager (production mode)
            project_id = os.environ.get('GCP_PROJECT_ID')
            if not project_id:
                return False, {"error": "Neither HTTP_TRIGGER_PRIVATE_KEY nor GCP_PROJECT_ID environment variable is set"}, request_id
            
            try:
                private_key = get_secret('CRE_AI_DEMO_HTTP_TRIGGER_PRIVATE_KEY', project_id)
                logger.info("Successfully fetched private key from Secret Manager")
            except Exception as e:
                logger.error(f"Failed to fetch private key from Secret Manager: {str(e)}")
                return False, {"error": f"Failed to fetch private key: {str(e)}"}, request_id
        
        # Convert input_data to dict for JSON-RPC request
        input_dict = input_data.model_dump()
        
        # Create JSON-RPC request
        jsonrpc_request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "workflows.execute",
            "params": {
                "input": input_dict,
                "workflow": {
                    "workflowID": workflow_id
                }
            }
        }
        
        logger.info(f"Triggering workflow {workflow_id}")
        logger.info(f"Gateway URL: {gateway_url}")
        logger.info(f"Input data: {json.dumps(input_dict)}")
        
        # Create and sign JWT
        jwt_token = create_jwt(jsonrpc_request, private_key)
        account = Account.from_key(private_key)
        logger.info(f"Signed by: {account.address}")
        
        # Send HTTP request to gateway
        response = requests.post(
            gateway_url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {jwt_token}"
            },
            json=jsonrpc_request,
            timeout=30
        )
        
        # Check response status
        if response.status_code != 200:
            logger.error(f"Gateway returned HTTP {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False, {
                "error": f"Gateway returned HTTP {response.status_code}",
                "detail": response.text
            }, request_id
        
        # Parse and return response
        try:
            result = response.json()
            logger.info(f"Workflow triggered successfully")
            return True, result, request_id
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {response.text}")
            return False, {
                "error": "Failed to parse gateway response",
                "detail": str(e),
                "raw_response": response.text
            }, request_id
            
    except requests.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        return False, {
            "error": "Failed to connect to gateway",
            "detail": str(e)
        }, request_id
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return False, {
            "error": "Internal error",
            "detail": str(e)
        }, request_id

