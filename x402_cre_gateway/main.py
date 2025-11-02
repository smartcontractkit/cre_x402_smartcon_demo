import os
import json
import logging
from typing import Any, Dict
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from x402.fastapi.middleware import require_payment
from cdp.x402 import create_facilitator_config, FacilitatorConfig

from utils import get_secret, execute_workflow_trigger

# Load environment variables from .env file (for local development)
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="X402 CRE Gateway")

# Load CDP API credentials
# Try to load from Google Secret Manager if GCP_PROJECT_ID is available
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
if GCP_PROJECT_ID:
    try:
        CDP_API_KEY_ID = get_secret("CDP_API_KEY_ID", GCP_PROJECT_ID)
        CDP_API_KEY_SECRET = get_secret("CDP_API_KEY_SECRET", GCP_PROJECT_ID)
        logger.info("Loaded CDP API credentials from Google Secret Manager")
    except Exception as e:
        logger.warning(f"Failed to load CDP credentials from Secret Manager: {e}, falling back to environment variables")
        CDP_API_KEY_ID = os.getenv("CDP_API_KEY_ID")
        CDP_API_KEY_SECRET = os.getenv("CDP_API_KEY_SECRET")
else:
    CDP_API_KEY_ID = os.getenv("CDP_API_KEY_ID")
    CDP_API_KEY_SECRET = os.getenv("CDP_API_KEY_SECRET")
    logger.info("Loaded CDP API credentials from environment variables")

# Create facilitator config
FACILITATOR_URL = os.getenv("FACILITATOR_URL")
if FACILITATOR_URL:
    logger.info(f"Using custom facilitator URL: {FACILITATOR_URL}")
    facilitator_config = FacilitatorConfig(
        url=FACILITATOR_URL,
    )
else:
    facilitator_config = create_facilitator_config(
        api_key_id=CDP_API_KEY_ID,
        api_key_secret=CDP_API_KEY_SECRET,
    )

if os.getenv("X402_NETWORK") == "base":
    app.middleware("http")(
        require_payment(
            path="/trigger_workflow_x402",
            price=os.getenv("X402_PRICE"),
            pay_to_address=os.getenv("X402_PAY_TO_ADDRESS"),
            network=os.getenv("X402_NETWORK"),
            facilitator_config=facilitator_config,
        )
    )
elif os.getenv("X402_NETWORK") == "base-sepolia":
    app.middleware("http")(
        require_payment(
            path="/trigger_workflow_x402",
            price=os.getenv("X402_PRICE"),
            pay_to_address=os.getenv("X402_PAY_TO_ADDRESS"),
            network=os.getenv("X402_NETWORK"),
        )
    )


# ============================================================================
# Request/Response Models
# ============================================================================

class WorkflowInput(BaseModel):
    """Input data for the MessageVault workflow"""
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
