import os
import json
import time
import uuid
import hashlib
import base64
import logging
from typing import Any, Dict, Tuple
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from eth_account import Account
from eth_account.messages import encode_defunct
from google.cloud import secretmanager
from dotenv import load_dotenv
from x402.fastapi.middleware import require_payment
from cdp.x402 import create_facilitator_config

# Load environment variables from .env file (for local development)
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="X402 CRE Gateway")

# Load CDP API credentials
CDP_API_KEY_ID = os.getenv("CDP_API_KEY_ID")
CDP_API_KEY_SECRET = os.getenv("CDP_API_KEY_SECRET")

facilitator_config = create_facilitator_config(
    api_key_id=CDP_API_KEY_ID,
    api_key_secret=CDP_API_KEY_SECRET,
)

# Define paths that require x402 payment
X402_PROTECTED_PATHS = [
    "/trigger_workflow_x402",
    "/hello_x402",
]

# Apply x402 payment middleware to protected routes
for path in X402_PROTECTED_PATHS:
    network = os.getenv("X402_NETWORK")
    
    # Build middleware config - only pass facilitator_config for mainnet (base)
    middleware_config = {
        "path": path,
        "price": os.getenv("X402_PRICE"),
        "pay_to_address": os.getenv("X402_PAY_TO_ADDRESS"),
        "network": network,
    }
    
    # Only include facilitator_config for base mainnet
    if network == "base":
        middleware_config["facilitator_config"] = facilitator_config
    
    app.middleware("http")(require_payment(**middleware_config))

# ============================================================================
# Request/Response Models
# ============================================================================

class WorkflowInput(BaseModel):
    """Input data for the MessageVault workflow"""
    recipient: str
    messages: list[str]

class TriggerWorkflowRequest(BaseModel):
    """Request to trigger the workflow with validated input"""
    input_data: WorkflowInput

class TriggerWorkflowResponse(BaseModel):
    success: bool
    response: Dict[str, Any]
    request_id: str

class HelloX402Request(BaseModel):
    data: Dict[str, Any] = {}

class HelloX402Response(BaseModel):
    hello: str

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

def execute_workflow_trigger(input_data: WorkflowInput) -> Tuple[bool, Dict[str, Any], str]:
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


# ============================================================================
# API Endpoints
# ============================================================================

@app.get('/hello')
def root():
    return {"hello": "world"}


@app.post('/hello_x402', response_model=HelloX402Response)
def hello_x402(request: HelloX402Request):
    """
    Test endpoint with x402 payment requirement
    
    Args:
        request: HelloX402Request containing optional data
    
    Returns:
        HelloX402Response with hello message
    """
    logger.info(f"[/hello_x402] Received request with body: {json.dumps(request.data, indent=2)}")
    return HelloX402Response(hello="x402")


@app.post('/trigger_workflow_x402', response_model=TriggerWorkflowResponse, status_code=200)
def trigger_workflow_x402(request: TriggerWorkflowRequest):
    """
    Trigger a CRE workflow by sending a signed JWT to the gateway (Requires x402 payment)
    
    NOTE: This endpoint ALWAYS returns HTTP 200, even on errors.
          Check the 'success' field in the response to determine if the workflow was triggered successfully.
    
    Expected input format:
    {
        "input_data": {
            "messages": ["Message 1", "Message 2"]
        }
    }
    
    Args:
        request: TriggerWorkflowRequest containing input_data with messages array
    
    Returns:
        TriggerWorkflowResponse with:
        - success: bool indicating if workflow triggered successfully
        - response: gateway response (on success) or error details (on failure)
        - request_id: UUID of the request
    """
    logger.info(f"[/trigger_workflow_x402] Received request")
    logger.info(f"[/trigger_workflow_x402] Message count: {len(request.input_data.messages)}")
    success, response_data, request_id = execute_workflow_trigger(request.input_data)
    
    if success:
        logger.info(f"[/trigger_workflow_x402] Successfully triggered workflow - request_id: {request_id}")
    else:
        logger.warning(f"[/trigger_workflow_x402] Failed to trigger workflow - request_id: {request_id}, error: {response_data.get('error', 'Unknown')}")
    
    return TriggerWorkflowResponse(
        success=success,
        response=response_data,
        request_id=request_id
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
