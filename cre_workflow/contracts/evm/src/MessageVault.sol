// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import "./keystone/IReceiver.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/// @title MessageVault - A contract for storing message hashes on-chain with workflow validation
/// @notice This contract stores message hashes and emits full content in events
/// @dev Uses workflow owner and name validation. Contract owner can update expected values.
contract MessageVault is IReceiver, Ownable {

    // Expected workflow validation values (modifiable by owner)
    address public expectedWorkflowOwner;
    bytes10 public expectedWorkflowName;
    
    // Trusted Chainlink KeystoneForwarder address (immutable)
    address public immutable forwarder;

    // Custom errors
    error InvalidSender(address sender, address expected);
    error InvalidWorkflowOwner(address received, address expected);
    error InvalidWorkflowName(bytes10 received, bytes10 expected);
    
    // Events for configuration changes
    event ExpectedWorkflowOwnerUpdated(address indexed oldOwner, address indexed newOwner);
    event ExpectedWorkflowNameUpdated(bytes10 indexed oldName, bytes10 indexed newName);
    
    struct MessageRecord {
        bytes32 contentHash;
        uint256 timestamp;
    }
    
    // Array of all message records (only hashes stored)
    MessageRecord[] public messageRecords;
    
    // Total message count
    uint256 private totalMessages;
    
    event MessageStored(
        uint256 indexed messageId,
        bytes32 indexed messageHash,
        string message,
        uint256 timestamp
    );
    
    /// @notice Constructor to set initial expected workflow values and forwarder
    /// @param _forwarderAddress Address of the Chainlink KeystoneForwarder
    /// @param _expectedWorkflowOwner Expected workflow owner address
    /// @param _expectedWorkflowName Expected workflow name (10 bytes)
    /// @dev Sepolia Forwarder: 0x15fC6ae953E024d975e77382eEeC56A9101f9F88
    constructor(
        address _forwarderAddress,
        address _expectedWorkflowOwner,
        bytes10 _expectedWorkflowName
    ) Ownable(msg.sender) {
        forwarder = _forwarderAddress;
        expectedWorkflowOwner = _expectedWorkflowOwner;
        expectedWorkflowName = _expectedWorkflowName;
    }
    
    /// @notice Update expected workflow owner (only callable by contract owner)
    /// @param _newWorkflowOwner New workflow owner address
    function setExpectedWorkflowOwner(address _newWorkflowOwner) external onlyOwner {
        address oldOwner = expectedWorkflowOwner;
        expectedWorkflowOwner = _newWorkflowOwner;
        emit ExpectedWorkflowOwnerUpdated(oldOwner, _newWorkflowOwner);
    }
    
    /// @notice Update expected workflow name (only callable by contract owner)
    /// @param _newWorkflowName New workflow name (10 bytes)
    function setExpectedWorkflowName(bytes10 _newWorkflowName) external onlyOwner {
        bytes10 oldName = expectedWorkflowName;
        expectedWorkflowName = _newWorkflowName;
        emit ExpectedWorkflowNameUpdated(oldName, _newWorkflowName);
    }
    
    /// @notice IReceiver implementation for Chainlink CRE
    /// @dev This is called when the workflow sends a report to this contract
    /// @dev rawReport format: ABI-encoded (string[] messages)
    /// @dev Multi-layered security: forwarder check + workflow validation
    function onReport(
        bytes calldata metadata,
        bytes calldata rawReport
    ) external override {
        // Layer 1: Verify caller is the trusted forwarder
        if (msg.sender != forwarder) {
            revert InvalidSender(msg.sender, forwarder);
        }

        // Layer 2: Decode and validate workflow metadata
        (address workflowOwner, bytes10 workflowName) = _decodeMetadata(metadata);

        if (workflowOwner != expectedWorkflowOwner) {
            revert InvalidWorkflowOwner(workflowOwner, expectedWorkflowOwner);
        }
        if (workflowName != expectedWorkflowName) {
            revert InvalidWorkflowName(workflowName, expectedWorkflowName);
        }

        // Decode ABI-encoded data: (string[])
        string[] memory messages = abi.decode(rawReport, (string[]));
        
        require(messages.length > 0, "At least one message required");
        
        // Store each message hash and emit full content
        uint256 storedCount = 0;
        uint256 timestamp = block.timestamp;
        
        for (uint256 i = 0; i < messages.length; i++) {
            // Skip empty messages
            if (bytes(messages[i]).length == 0) {
                continue;
            }
            
            bytes32 hash = keccak256(abi.encodePacked(messages[i]));
            
            // Create and store message record (only hash, not content)
            MessageRecord memory newRecord = MessageRecord({
                contentHash: hash,
                timestamp: timestamp
            });
            
            messageRecords.push(newRecord);
            uint256 messageId = messageRecords.length - 1;
            
            totalMessages++;
            storedCount++;
            
            // Emit event with full content (for off-chain indexing)
            emit MessageStored(messageId, hash, messages[i], timestamp);
        }
        
        require(storedCount > 0, "No valid messages to store");
    }
    
    /// @notice Get total number of messages stored
    function getTotalMessages() external view returns (uint256) {
        return totalMessages;
    }
    
    /// @notice Get a specific message record by ID (hash and timestamp only, no content)
    function getMessageRecord(uint256 messageId) external view returns (
        bytes32 contentHash,
        uint256 timestamp
    ) {
        require(messageId < messageRecords.length, "Message does not exist");
        MessageRecord memory record = messageRecords[messageId];
        return (record.contentHash, record.timestamp);
    }
    
    /// @notice Verify a message content against a stored hash
    function verifyMessage(uint256 messageId, string calldata content) external view returns (bool) {
        require(messageId < messageRecords.length, "Message does not exist");
        bytes32 hash = keccak256(abi.encodePacked(content));
        return messageRecords[messageId].contentHash == hash;
    }
    
  /// @notice Extracts the workflow name and the workflow owner from the metadata parameter of onReport
  /// @param metadata The metadata in bytes format
  /// @return workflowOwner The owner of the workflow
  /// @return workflowName  The name of the workflow
  function _decodeMetadata(bytes memory metadata) internal pure returns (address, bytes10) {
    address workflowOwner;
    bytes10 workflowName;
    // (first 32 bytes contain length of the byte array)
    // workflow_id             // offset 32, size 32
    // workflow_name            // offset 64, size 10
    // workflow_owner           // offset 74, size 20
    // report_name              // offset 94, size  2
    assembly {
      // no shifting needed for bytes10 type
      workflowName := mload(add(metadata, 64))
      workflowOwner := shr(mul(12, 8), mload(add(metadata, 74)))
    }
    return (workflowOwner, workflowName);
  }

    /// @notice Override supportsInterface to include IReceiver
    function supportsInterface(
        bytes4 interfaceId
    ) public pure virtual override returns (bool) {
        return
            interfaceId == type(IReceiver).interfaceId ||
            interfaceId == type(IERC165).interfaceId;
    }
}
