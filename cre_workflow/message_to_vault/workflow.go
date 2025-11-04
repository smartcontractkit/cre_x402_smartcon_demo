package main

import (
	"encoding/json"
	"fmt"
	"log/slog"
	"strings"
	"sync"

	messagevault "cre_workflow/contracts/evm/src/generated/message_vault"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	pb "github.com/smartcontractkit/chainlink-protos/cre/go/sdk"
	"github.com/smartcontractkit/cre-sdk-go/capabilities/blockchain/evm"
	"github.com/smartcontractkit/cre-sdk-go/capabilities/networking/http"
	"github.com/smartcontractkit/cre-sdk-go/cre"
)

// EvmConfig holds the EVM chain and contract configuration
type EvmConfig struct {
	ChainSelector       uint64 `json:"chainSelector"` // CCIP chain selector
	MessageVaultAddress string `json:"messageVaultAddress"`
	GasLimit            uint64 `json:"gasLimit"`
}

func (e *EvmConfig) GetChainSelector() uint64 {
	return e.ChainSelector
}

func (e *EvmConfig) NewEVMClient() *evm.Client {
	return &evm.Client{ChainSelector: e.ChainSelector}
}

// Config is the workflow configuration loaded from config.json
type Config struct {
	Evms []EvmConfig `json:"evms"`
}

// HTTPPayload wraps the input data
type HTTPPayload struct {
	Input MessageVaultRequest `json:"input"`
}

// MessageVaultRequest holds the input from the HTTP payload
type MessageVaultRequest struct {
	Messages []string `json:"messages"` // Array of messages
}

// TxResult holds the result of a single transaction
type TxResult struct {
	TxHash        string `json:"txHash"`
	ChainSelector uint64 `json:"chainSelector"`
	Contract      string `json:"contract"`
}

// WorkflowResult holds the result of storing messages
type WorkflowResult struct {
	Transactions []TxResult `json:"transactions"`
	MessageCount int        `json:"messageCount"`
}

func InitWorkflow(config *Config, logger *slog.Logger, secretsProvider cre.SecretsProvider) (cre.Workflow[*Config], error) {
	// You can set up multiple authorized keys
	MyAuthorizedKeys := []*http.AuthorizedKey{
		{
			Type:      http.KeyType_KEY_TYPE_ECDSA_EVM,
			PublicKey: "your_http_trigger_private_key",
		},
	}
	httpTriggerCfg := &http.Config{AuthorizedKeys: MyAuthorizedKeys}

	return cre.Workflow[*Config]{
		cre.Handler(
			http.Trigger(httpTriggerCfg),
			onHTTPTrigger,
		),
	}, nil
}

func onHTTPTrigger(config *Config, runtime cre.Runtime, payload *http.Payload) (*WorkflowResult, error) {
	logger := runtime.Logger()
	logger.Info("HTTP trigger received - storing messages")

	// Parse the input from payload
	logger.Info("Raw payload.Input", "bytes", string(payload.Input))

	var vaultRequest MessageVaultRequest
	if err := json.Unmarshal(payload.Input, &vaultRequest); err != nil {
		logger.Error("Failed to parse payload", "err", err, "raw", string(payload.Input))
		return nil, fmt.Errorf("failed to parse payload: %w", err)
	}

	// Validate inputs - workflow will revert if any validation fails
	if len(vaultRequest.Messages) == 0 {
		logger.Error("Validation failed: at least one message is required")
		return nil, fmt.Errorf("at least one message is required")
	}

	logger.Info("Parsed request", "message_count", len(vaultRequest.Messages))
	logger.Info("Validation passed, proceeding to store messages")

	transactions, messageCount, err := storeMessages(config, runtime, vaultRequest.Messages)
	if err != nil {
		logger.Error("Failed to store messages", "err", err)
		return nil, fmt.Errorf("failed to store messages: %w", err)
	}

	return &WorkflowResult{
		Transactions: transactions,
		MessageCount: messageCount,
	}, nil
}

// storeMessages calls the onReport() function on the MessageVault contract via WriteReport
// It writes to all configured EVM contracts in parallel
func storeMessages(config *Config, runtime cre.Runtime, messages []string) ([]TxResult, int, error) {
	logger := runtime.Logger()

	if len(config.Evms) == 0 {
		return nil, 0, fmt.Errorf("no EVM configuration found")
	}

	// Filter out empty messages first
	var validMessages []string
	for _, msg := range messages {
		if strings.TrimSpace(msg) != "" {
			validMessages = append(validMessages, msg)
		}
	}

	if len(validMessages) == 0 {
		return nil, 0, fmt.Errorf("no valid messages to send")
	}

	logger.Info("Prepared messages", "count", len(validMessages))

	// Structures for parallel execution
	type writeResult struct {
		txResult TxResult
		err      error
	}

	var (
		wg      sync.WaitGroup
		mu      sync.Mutex
		results []writeResult
	)

	// Launch parallel writes to all configured contracts
	for i, evmConfig := range config.Evms {
		// Validate vault address is configured
		if evmConfig.MessageVaultAddress == "" || evmConfig.MessageVaultAddress == "0xYOUR_DEPLOYED_CONTRACT_ADDRESS" {
			logger.Warn("Skipping EVM config - address not configured", "chainSelector", evmConfig.ChainSelector)
			continue
		}

		wg.Add(1)
		go func(index int, cfg EvmConfig) {
			defer wg.Done()

			logger.Info("Processing EVM config in parallel", "index", index, "chainSelector", cfg.ChainSelector)
			logger.Info("Storing messages", "contractAddress", cfg.MessageVaultAddress, "chainSelector", cfg.ChainSelector)

			// Create EVM client
			evmClient := cfg.NewEVMClient()

			// Create contract instance
			contractAddress := common.HexToAddress(cfg.MessageVaultAddress)
			contract, err := messagevault.NewMessageVault(evmClient, contractAddress, nil)
			if err != nil {
				logger.Error("Failed to create contract instance", "chainSelector", cfg.ChainSelector, "err", err)
				mu.Lock()
				results = append(results, writeResult{err: fmt.Errorf("failed to create contract instance for chain %d: %w", cfg.ChainSelector, err)})
				mu.Unlock()
				return
			}

			// Prepare gas configuration
			gasConfig := &evm.GasConfig{GasLimit: cfg.GasLimit}

			logger.Info("Sending report to contract via onReport()", "chainSelector", cfg.ChainSelector)

			// ABI-encode the data: (string[])
			stringArrayType, err := abi.NewType("string[]", "", nil)
			if err != nil {
				logger.Error("Failed to create string array ABI type", "chainSelector", cfg.ChainSelector, "err", err)
				mu.Lock()
				results = append(results, writeResult{err: fmt.Errorf("failed to create string array ABI type for chain %d: %w", cfg.ChainSelector, err)})
				mu.Unlock()
				return
			}

			arguments := abi.Arguments{
				{Type: stringArrayType},
			}

			encoded, err := arguments.Pack(validMessages)
			if err != nil {
				logger.Error("Failed to ABI-encode data", "chainSelector", cfg.ChainSelector, "err", err)
				mu.Lock()
				results = append(results, writeResult{err: fmt.Errorf("failed to ABI-encode data for chain %d: %w", cfg.ChainSelector, err)})
				mu.Unlock()
				return
			}

			logger.Info("ABI-encoded payload", "chainSelector", cfg.ChainSelector, "size", len(encoded), "message_count", len(validMessages))

			// Generate a signed report with the encoded data
			report, err := runtime.GenerateReport(&pb.ReportRequest{
				EncodedPayload: encoded,
				EncoderName:    "evm",
				SigningAlgo:    "ecdsa",
				HashingAlgo:    "keccak256",
			}).Await()
			if err != nil {
				logger.Error("Failed to generate report", "chainSelector", cfg.ChainSelector, "err", err)
				mu.Lock()
				results = append(results, writeResult{err: fmt.Errorf("failed to generate report for chain %d: %w", cfg.ChainSelector, err)})
				mu.Unlock()
				return
			}

			// Write the report to the contract (calls onReport and stores messages)
			resp, err := contract.WriteReport(runtime, report, gasConfig).Await()
			if err != nil {
				logger.Error("Failed to write report to contract", "chainSelector", cfg.ChainSelector, "err", err)
				mu.Lock()
				results = append(results, writeResult{err: fmt.Errorf("failed to write report to contract for chain %d: %w", cfg.ChainSelector, err)})
				mu.Unlock()
				return
			}

			txHash := fmt.Sprintf("0x%x", resp.TxHash)

			logger.Info("Successfully stored messages via onReport", "chainSelector", cfg.ChainSelector, "txHash", txHash, "message_count", len(validMessages))

			// Add successful transaction result
			mu.Lock()
			results = append(results, writeResult{
				txResult: TxResult{
					TxHash:        txHash,
					ChainSelector: cfg.ChainSelector,
					Contract:      cfg.MessageVaultAddress,
				},
			})
			mu.Unlock()
		}(i, evmConfig)
	}

	// Wait for all parallel operations to complete
	wg.Wait()

	// Collect successful transactions and errors
	var txResults []TxResult
	var errors []error

	for _, result := range results {
		if result.err != nil {
			errors = append(errors, result.err)
		} else {
			txResults = append(txResults, result.txResult)
		}
	}

	// Log summary
	logger.Info("Parallel execution completed", "successful", len(txResults), "failed", len(errors))

	// Check if we successfully wrote to at least one contract
	if len(txResults) == 0 {
		// All failed - return combined error
		if len(errors) > 0 {
			return nil, 0, fmt.Errorf("failed to write to any configured contracts: %v", errors)
		}
		return nil, 0, fmt.Errorf("no contracts were processed")
	}

	// Log any errors but still return success if at least one succeeded
	for _, err := range errors {
		logger.Warn("Some transactions failed", "error", err)
	}

	logger.Info("Successfully completed transactions", "count", len(txResults))
	return txResults, len(validMessages), nil
}
