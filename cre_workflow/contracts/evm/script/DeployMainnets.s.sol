// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import {Script, console} from "forge-std/Script.sol";
import {MessageVault} from "../src/MessageVault.sol";

contract DeployMainnetsScript is Script {
    function run() public {

        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");

        // Read configuration from environment variables
        address ethereumForwarder = vm.envAddress("ETHEREUM_FORWARDER");
        address baseForwarder = vm.envAddress("BASE_FORWARDER");
        address workflowOwner = vm.envAddress("WORKFLOW_OWNER");
        
        // Read workflow name as string and convert to bytes10
        string memory workflowNameStr = vm.envString("WORKFLOW_NAME");
        // Workflow Names are stored as truncated bytes10 in the report metdata
        // forge-lint: disable-next-line(unsafe-typecast)
        bytes10 workflowName = bytes10(bytes(workflowNameStr));
        
        // Deploy to Ethereum Mainnet
        vm.createSelectFork("ethereum");
        vm.startBroadcast(deployerPrivateKey);
        MessageVault ethereumVault = new MessageVault(
            ethereumForwarder,
            workflowOwner,
            workflowName
        );
        console.log("Ethereum MessageVault deployed at:", address(ethereumVault));
        vm.stopBroadcast();

        // Deploy to Base Mainnet
        vm.createSelectFork("base");
        vm.startBroadcast(deployerPrivateKey);
        MessageVault baseVault = new MessageVault(
            baseForwarder,
            workflowOwner,
            workflowName
        );
        console.log("Base MessageVault deployed at:", address(baseVault));
        vm.stopBroadcast();
    }
}

