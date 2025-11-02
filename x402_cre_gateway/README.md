# X402 CRE Gateway Docker

FastAPI service that triggers CRE workflows with JWT signing, with optional x402 payment integration.

## Features

- `/trigger_workflow` - Trigger workflow without payment
- `/trigger_workflow_x402` - Trigger workflow with x402 payment requirement
- Automatic JWT signing with Ethereum private keys
- Environment-based configuration

## Environment Variables

Required:
- `WORKFLOW_ID` - CRE workflow ID
- `GATEWAY_URL` - CRE gateway URL
- `HTTP_TRIGGER_PRIVATE_KEY` - Ethereum private key for signing (local) or use Secret Manager

Optional (for x402 payment):
- `X402_PRICE` - Payment amount (e.g., "0.001")
- `X402_PAY_TO_ADDRESS` - Address to receive payments
- `X402_NETWORK` - Network name (e.g., "base-sepolia")

## Build & Run

```bash
# Build
docker build -t cre-demo-ai-x402-gateway 3_x402_cre_gateway_docker

# Run
docker run -p 5002:5000 \
  --env-file .env \
  cre-demo-ai-x402-gateway:latest
```

## Usage

### Free endpoint (no payment):
```bash
curl -X POST http://localhost:5002/trigger_workflow \
  -H "Content-Type: application/json" \
  -d '{
    "input_data": {
      "recipient": "0x1B6709d6c53EB71B9ADF0c66F36bF994ed21DF79",
      "messages": [
        "First message",
        "Second message",
        "Third message"
      ]
    }
  }'
```

### Paid endpoint (requires x402 payment):
```bash
curl -X POST http://localhost:5002/trigger_workflow_x402 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_X402_TOKEN" \
  -d '{
    "input_data": {
      "recipient": "0x1B6709d6c53EB71B9ADF0c66F36bF994ed21DF79",
      "messages": [
        "First message",
        "Second message",
        "Third message"
      ]
    }
  }'
```