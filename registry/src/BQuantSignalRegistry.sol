// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract BQuantSignalRegistry {

    enum Signal { FLAT, LONG, SHORT }

    struct SignalLog {
        address token;
        Signal signal;
        int256 driftBps;
        uint8 confidence;
        uint256 timestamp;
    }

    SignalLog[] public logs;

    event SignalLogged(
        uint256 indexed logId,
        address indexed token,
        Signal signal,
        int256 driftBps,
        uint8 confidence,
        uint256 timestamp
    );

    function logSignal(
        address token,
        Signal signal,
        int256 driftBps,
        uint8 confidence
    ) external {
        require(confidence <= 100, "confidence must be 0-100");

        logs.push(SignalLog({
            token: token,
            signal: signal,
            driftBps: driftBps,
            confidence: confidence,
            timestamp: block.timestamp
        }));

        emit SignalLogged(logs.length - 1, token, signal, driftBps, confidence, block.timestamp);
    }

    function getLog(uint256 logId) external view returns (SignalLog memory) {
        return logs[logId];
    }

    function totalLogs() external view returns (uint256) {
        return logs.length;
    }
}
