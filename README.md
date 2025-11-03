# CRE x X402 Demo

A demonstration of integrating [Chainlink Runtime Environment (CRE)](https://docs.chain.link/chainlink-functions) workflows with the [X402 payment protocol](https://docs.cdp.coinbase.com/x402/docs/welcome) using Coinbase Developer Platform.

## Overview

This project combines:
- **CRE Workflow**: Chainlink workflow that receives messages and stores them on-chain in a MessageVault contract
- **X402 Gateway**: FastAPI service that triggers workflows with optional crypto payment requirements
- **MessageVault Contract**: Solidity smart contract that validates and stores message hashes on Ethereum/Base

## Architecture

```
User Payment → X402 Gateway → JWT-signed Request → CRE Workflow → MessageVault Contract
```

1. User sends messages with X402 payment to the gateway
2. Gateway validates payment and creates JWT-signed workflow trigger
3. CRE workflow receives messages and writes hashes to smart contract
4. MessageVault validates workflow sender and stores data on-chain

## Project Structure

```
cre_x402_demo/
├── cre_workflow/              # Chainlink Runtime Environment workflow
│   ├── contracts/evm/         # Smart contracts (Foundry)
│   │   └── src/
│   │       └── MessageVault.sol
│   └── message_to_vault/      # Go workflow logic
│       ├── workflow.go
│       └── config.production.json
└── x402_cre_gateway/          # FastAPI payment gateway
    ├── main.py
    ├── utils.py
    └── Dockerfile
```

## Quick Start

### 1. Deploy MessageVault Contract

```bash
cd cre_workflow/contracts/evm
cp env.example .env
# Edit .env with your values

forge script script/DeployTestnets.s.sol --broadcast --multi
```

### 2. Deploy CRE Workflow

```bash
cd cre_workflow/message_to_vault

# Deploy to staging
cre workflow deploy --target staging-settings

# Or deploy to production
cre workflow deploy --target production-settings
```

### 3. Run X402 Gateway

```bash
cd x402_cre_gateway
cp .env_example .env
# Edit .env with your credentials

pip install -r requirements.txt
python main.py
```

Or with Docker:
```bash
docker build -t x402-gateway .
docker run -p 8080:8080 --env-file .env x402-gateway
```

## Configuration

### Gateway Environment Variables

Required:
- `WORKFLOW_ID` - Your CRE workflow ID
- `GATEWAY_URL` - CRE gateway URL (default: https://01.gateway.zone-a.cre.chain.link)
- `HTTP_TRIGGER_PRIVATE_KEY` - Ethereum private key for signing

For X402 payments:
- `X402_PRICE` - Payment amount (e.g., "0.01")
- `X402_PAY_TO_ADDRESS` - Address to receive payments
- `X402_NETWORK` - Network ("base" or "base-sepolia")
- `CDP_API_KEY_ID` - Coinbase Developer Platform API key ID
- `CDP_API_KEY_SECRET` - CDP API key secret

### Contract Configuration

See `cre_workflow/contracts/evm/env.example` for deployment configuration.

## API Usage

### Free Endpoint (No Payment)

```bash
curl -X POST http://localhost:8080/hello \
  -H "Content-Type: application/json"
```

### Paid Endpoint (Requires X402 Payment)

```bash
curl -X POST http://localhost:8080/trigger_workflow_x402 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_X402_TOKEN" \
  -d '{
    "input_data": {
      "messages": ["Hello from X402", "Second message"]
    }
  }'
```

## Key Features

- ✅ Decentralized workflow execution via Chainlink CRE
- ✅ Crypto payments via X402 protocol on Base
- ✅ On-chain message storage with validation
- ✅ JWT-signed workflow triggers for security
- ✅ Support for multiple chains (Ethereum, Base)
- ✅ GCP Secret Manager integration for production

## Technologies Used

- **Chainlink CRE**: Decentralized workflow orchestration
- **X402**: Onchain payment protocol (Coinbase)
- **Solidity**: Smart contract development
- **Foundry**: Ethereum development toolkit
- **FastAPI**: Python web framework
- **Go**: CRE workflow implementation

## License

MIT
