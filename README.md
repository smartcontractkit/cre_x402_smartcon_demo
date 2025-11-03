# CRE x X402 Demo

A demonstration of how to trigger [Chainlink Runtime Environment (CRE)](https://cre.chain.link) workflows by exposing a [X402](https://docs.cdp.coinbase.com/x402/docs/welcome) endpoint.

## Overview

This project combines:
- **CRE Workflow**: CRE workflow that receives messages and stores them on-chain in a MessageVault contract.
- **MessageVault Contract**: Solidity smart contract that validates and stores message hashes on Ethereum/Base.
- **X402 Gateway**: FastAPI service that triggers a CRE workflow when crypto payment requirements are fulfilled.

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
├── cre_workflow/              # CRE workflow
│   ├── contracts/evm/         # Smart contracts (Foundry)
│   │   └── src/
│   │       └── MessageVault.sol
│   └── message_to_vault/      # Workflow logic
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
cd cre_workflow

cp env.example .env
# Edit .env with your credentials

# Deploy to staging
cre workflow deploy --target staging-settings

# Or deploy to production
cre workflow deploy --target production-settings
```

### 3. Run X402 Gateway

Local Docker:
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
- `CDP_API_KEY_ID` - Coinbase Developer Platform API key ID [To use CDP Facilitator]
- `CDP_API_KEY_SECRET` - CDP API key secret [To use CDP Facilitator]
- `F` - CDP API key secret


### Contract Configuration

See `cre_workflow/contracts/evm/env.example` for deployment configuration.


## License

MIT

## Disclaimer

This tutorial represents an educational example to use a Chainlink system, product, or service and is provided to demonstrate how to interact with Chainlink’s systems, products, and services to integrate them into your own. This template is provided “AS IS” and “AS AVAILABLE” without warranties of any kind, it has not been audited, and it may be missing key checks or error handling to make the usage of the system, product or service more clear. Do not use the code in this example in a production environment without completing your own audits and application of best practices. Neither Chainlink Labs, the Chainlink Foundation, nor Chainlink node operators are responsible for unintended outputs that are generated due to errors in code.





