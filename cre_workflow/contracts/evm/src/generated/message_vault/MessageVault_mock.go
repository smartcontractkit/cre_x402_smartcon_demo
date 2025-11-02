// Code generated — DO NOT EDIT.

//go:build !wasip1

package message_vault

import (
	"errors"
	"fmt"
	"math/big"

	"github.com/ethereum/go-ethereum/common"
	evmmock "github.com/smartcontractkit/cre-sdk-go/capabilities/blockchain/evm/mock"
)

var (
	_ = errors.New
	_ = fmt.Errorf
	_ = big.NewInt
	_ = common.Big1
)

// MessageVaultMock is a mock implementation of MessageVault for testing.
type MessageVaultMock struct {
	ExpectedWorkflowName  func() ([10]byte, error)
	ExpectedWorkflowOwner func() (common.Address, error)
	Forwarder             func() (common.Address, error)
	GetMessageRecord      func(GetMessageRecordInput) (GetMessageRecordOutput, error)
	GetTotalMessages      func() (*big.Int, error)
	MessageRecords        func(MessageRecordsInput) (MessageRecordsOutput, error)
	Owner                 func() (common.Address, error)
	VerifyMessage         func(VerifyMessageInput) (bool, error)
}

// NewMessageVaultMock creates a new MessageVaultMock for testing.
func NewMessageVaultMock(address common.Address, clientMock *evmmock.ClientCapability) *MessageVaultMock {
	mock := &MessageVaultMock{}

	codec, err := NewCodec()
	if err != nil {
		panic("failed to create codec for mock: " + err.Error())
	}

	abi := codec.(*Codec).abi
	_ = abi

	funcMap := map[string]func([]byte) ([]byte, error){
		string(abi.Methods["expectedWorkflowName"].ID[:4]): func(payload []byte) ([]byte, error) {
			if mock.ExpectedWorkflowName == nil {
				return nil, errors.New("expectedWorkflowName method not mocked")
			}
			result, err := mock.ExpectedWorkflowName()
			if err != nil {
				return nil, err
			}
			return abi.Methods["expectedWorkflowName"].Outputs.Pack(result)
		},
		string(abi.Methods["expectedWorkflowOwner"].ID[:4]): func(payload []byte) ([]byte, error) {
			if mock.ExpectedWorkflowOwner == nil {
				return nil, errors.New("expectedWorkflowOwner method not mocked")
			}
			result, err := mock.ExpectedWorkflowOwner()
			if err != nil {
				return nil, err
			}
			return abi.Methods["expectedWorkflowOwner"].Outputs.Pack(result)
		},
		string(abi.Methods["forwarder"].ID[:4]): func(payload []byte) ([]byte, error) {
			if mock.Forwarder == nil {
				return nil, errors.New("forwarder method not mocked")
			}
			result, err := mock.Forwarder()
			if err != nil {
				return nil, err
			}
			return abi.Methods["forwarder"].Outputs.Pack(result)
		},
		string(abi.Methods["getMessageRecord"].ID[:4]): func(payload []byte) ([]byte, error) {
			if mock.GetMessageRecord == nil {
				return nil, errors.New("getMessageRecord method not mocked")
			}
			inputs := abi.Methods["getMessageRecord"].Inputs

			values, err := inputs.Unpack(payload)
			if err != nil {
				return nil, errors.New("Failed to unpack payload")
			}
			if len(values) != 1 {
				return nil, errors.New("expected 1 input value")
			}

			args := GetMessageRecordInput{
				MessageId: values[0].(*big.Int),
			}

			result, err := mock.GetMessageRecord(args)
			if err != nil {
				return nil, err
			}
			return abi.Methods["getMessageRecord"].Outputs.Pack(
				result.ContentHash,
				result.Timestamp,
			)
		},
		string(abi.Methods["getTotalMessages"].ID[:4]): func(payload []byte) ([]byte, error) {
			if mock.GetTotalMessages == nil {
				return nil, errors.New("getTotalMessages method not mocked")
			}
			result, err := mock.GetTotalMessages()
			if err != nil {
				return nil, err
			}
			return abi.Methods["getTotalMessages"].Outputs.Pack(result)
		},
		string(abi.Methods["messageRecords"].ID[:4]): func(payload []byte) ([]byte, error) {
			if mock.MessageRecords == nil {
				return nil, errors.New("messageRecords method not mocked")
			}
			inputs := abi.Methods["messageRecords"].Inputs

			values, err := inputs.Unpack(payload)
			if err != nil {
				return nil, errors.New("Failed to unpack payload")
			}
			if len(values) != 1 {
				return nil, errors.New("expected 1 input value")
			}

			args := MessageRecordsInput{
				Arg0: values[0].(*big.Int),
			}

			result, err := mock.MessageRecords(args)
			if err != nil {
				return nil, err
			}
			return abi.Methods["messageRecords"].Outputs.Pack(
				result.ContentHash,
				result.Timestamp,
			)
		},
		string(abi.Methods["owner"].ID[:4]): func(payload []byte) ([]byte, error) {
			if mock.Owner == nil {
				return nil, errors.New("owner method not mocked")
			}
			result, err := mock.Owner()
			if err != nil {
				return nil, err
			}
			return abi.Methods["owner"].Outputs.Pack(result)
		},
		string(abi.Methods["verifyMessage"].ID[:4]): func(payload []byte) ([]byte, error) {
			if mock.VerifyMessage == nil {
				return nil, errors.New("verifyMessage method not mocked")
			}
			inputs := abi.Methods["verifyMessage"].Inputs

			values, err := inputs.Unpack(payload)
			if err != nil {
				return nil, errors.New("Failed to unpack payload")
			}
			if len(values) != 2 {
				return nil, errors.New("expected 2 input values")
			}

			args := VerifyMessageInput{
				MessageId: values[0].(*big.Int),
				Content:   values[1].(string),
			}

			result, err := mock.VerifyMessage(args)
			if err != nil {
				return nil, err
			}
			return abi.Methods["verifyMessage"].Outputs.Pack(result)
		},
	}

	evmmock.AddContractMock(address, clientMock, funcMap, nil)
	return mock
}
