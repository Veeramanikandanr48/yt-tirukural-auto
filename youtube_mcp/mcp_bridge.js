#!/usr/bin/env node
/**
 * MCP Bridge Script
 * Bridges Python calls to YouTube MCP Server
 * 
 * This script receives JSON-RPC requests from Python and forwards them to the MCP server
 */

const { spawn } = require('child_process');
const readline = require('readline');

// Get request from command line argument
const requestJson = process.argv[2];

if (!requestJson) {
    console.error(JSON.stringify({
        jsonrpc: "2.0",
        id: null,
        error: {
            code: -32600,
            message: "Invalid Request: No request provided"
        }
    }));
    process.exit(1);
}

let request;
try {
    request = JSON.parse(requestJson);
} catch (e) {
    console.error(JSON.stringify({
        jsonrpc: "2.0",
        id: request?.id || null,
        error: {
            code: -32700,
            message: "Parse error: " + e.message
        }
    }));
    process.exit(1);
}

// Spawn MCP server process
const mcpServer = spawn('zubeid-youtube-mcp-server', [], {
    env: process.env,
    stdio: ['pipe', 'pipe', 'pipe']
});

// Send request to MCP server
mcpServer.stdin.write(JSON.stringify(request) + '\n');
mcpServer.stdin.end();

// Read response from MCP server
let responseData = '';
mcpServer.stdout.on('data', (data) => {
    responseData += data.toString();
});

mcpServer.stderr.on('data', (data) => {
    console.error(data.toString());
});

mcpServer.on('close', (code) => {
    if (code !== 0) {
        console.error(JSON.stringify({
            jsonrpc: "2.0",
            id: request.id,
            error: {
                code: -32000,
                message: `Server error: Process exited with code ${code}`
            }
        }));
        process.exit(1);
    } else {
        // Try to parse response
        try {
            const response = JSON.parse(responseData);
            console.log(JSON.stringify(response));
        } catch (e) {
            // If not JSON, return as-is
            console.log(responseData);
        }
    }
});

// Timeout after 30 seconds
setTimeout(() => {
    mcpServer.kill();
    console.error(JSON.stringify({
        jsonrpc: "2.0",
        id: request.id,
        error: {
            code: -32000,
            message: "Timeout: Request took too long"
        }
    }));
    process.exit(1);
}, 30000);

