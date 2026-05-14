package com.deadlockcoach.replayparser;

public final class ReplayParserException extends RuntimeException {
    private final int exitCode;

    public ReplayParserException(int exitCode, String message) {
        super(message);
        this.exitCode = exitCode;
    }

    public int exitCode() {
        return exitCode;
    }
}
