// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import {Script, console} from "forge-std/Script.sol";
import {MessageVault} from "../src/MessageVault.sol";

contract DeployTestnetsScript is Script {
    function run() public {

        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");

        // Read configuration from environment variables
        address sepoliaForwarder = vm.envAddress("SEPOLIA_FORWARDER");
        address baseSepoliaForwarder = vm.envAddress("BASE_SEPOLIA_FORWARDER");
        address workflowOwner = vm.envAddress("WORKFLOW_OWNER");
        
        // Read workflow name as string and convert to bytes10
        string memory workflowNameStr = vm.envString("WORKFLOW_NAME");
        // Workflow Names are stored as truncated bytes10 in the report metdata
        // forge-lint: disable-next-line(unsafe-typecast)
        bytes10 workflowName = bytes10(bytes(workflowNameStr));
        
        // Deploy to Sepolia
        vm.createSelectFork("sepolia");
        vm.startBroadcast(deployerPrivateKey);
        MessageVault sepoliaVault = new MessageVault(
            sepoliaForwarder,
            workflowOwner,
            workflowName
        );
        console.log("Sepolia MessageVault deployed at:", address(sepoliaVault));
        vm.stopBroadcast();

        // Deploy to Base Sepolia
        vm.createSelectFork("base-sepolia");
        vm.startBroadcast(deployerPrivateKey);
        MessageVault baseSepoliaVault = new MessageVault(
            baseSepoliaForwarder,
            workflowOwner,
            workflowName
        );
        console.log("Base Sepolia MessageVault deployed at:", address(baseSepoliaVault));
        vm.stopBroadcast();
    }
}
