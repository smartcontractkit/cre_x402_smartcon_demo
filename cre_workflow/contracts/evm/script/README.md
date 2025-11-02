# Deployment Scripts

## Setup

1. **Copy the environment example file:**
   ```bash
   cp env.example .env
   ```

2. **Edit `.env` and fill in your values:**
   - `PRIVATE_KEY`: Your deployment wallet private key (with 0x prefix)
   - **Testnet Forwarders:**
     - `SEPOLIA_FORWARDER`: Chainlink Forwarder address for Sepolia
     - `BASE_SEPOLIA_FORWARDER`: Chainlink Forwarder address for Base Sepolia
   - **Mainnet Forwarders:**
     - `ETHEREUM_FORWARDER`: Chainlink Forwarder address for Ethereum
     - `BASE_FORWARDER`: Chainlink Forwarder address for Base
   - **Workflow Config:**
     - `WORKFLOW_OWNER`: Address of the workflow owner
     - `WORKFLOW_NAME`: Name of the workflow (max 10 bytes)
   - **Verification:**
     - `ETHERSCAN_API_KEY`: For contract verification (optional)
     - `BASESCAN_API_KEY`: For Base contract verification (optional)

## Deploy to Testnets

### Dry Run (Simulation)
Test the deployment without broadcasting:
```bash
forge script script/DeployTestnets.s.sol:DeployTestnetsScript -vvvv
```

### Deploy with Broadcast
Deploy to both Sepolia and Base Sepolia:
```bash
forge script script/DeployTestnets.s.sol:DeployTestnetsScript \
  --broadcast \
  -vvvv
```

### Deploy with Verification
Deploy and verify contracts on Etherscan/Basescan:
```bash
forge script script/DeployTestnets.s.sol:DeployTestnetsScript \
  --broadcast \
  --verify \
  -vvvv
```

## Deploy to Mainnets

⚠️ **WARNING: This deploys to production networks with real funds!**

### Dry Run (Simulation)
Test the deployment without broadcasting:
```bash
forge script script/DeployMainnets.s.sol:DeployMainnetsScript -vvvv
```

### Deploy with Broadcast
Deploy to both Ethereum and Base mainnets:
```bash
forge script script/DeployMainnets.s.sol:DeployMainnetsScript \
  --broadcast \
  -vvvv
```

### Deploy with Verification
Deploy and verify contracts on Etherscan/Basescan:
```bash
forge script script/DeployMainnets.s.sol:DeployMainnetsScript \
  --broadcast \
  --verify \
  -vvvv
```

## What the Scripts Do

### `DeployTestnets.s.sol`
1. Reads configuration from environment variables
2. Deploys MessageVault to Sepolia testnet
3. Deploys MessageVault to Base Sepolia testnet
4. Outputs the deployed contract addresses

### `DeployMainnets.s.sol`
1. Reads configuration from environment variables
2. Deploys MessageVault to Ethereum mainnet
3. Deploys MessageVault to Base mainnet
4. Outputs the deployed contract addresses

## Notes

- **Testnets:** Make sure your deployment wallet has ETH on both Sepolia and Base Sepolia
- **Mainnets:** Make sure your deployment wallet has sufficient ETH on both Ethereum and Base mainnet
- The scripts use public RPC endpoints by default (configured in `foundry.toml`)
- Deployment addresses will be saved in `broadcast/` directory
- Contract verification requires API keys from Etherscan and Basescan

