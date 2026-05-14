package com.deadlockcoach.replayparser;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class ReplayParserCliTest {
    @TempDir Path tempDir;

    @Test
    void missingInputArgumentReturnsInvalidArgs() {
        assertEquals(2, ReplayParserCli.run(new String[]{}));
    }

    @Test
    void missingFileReturnsInputError() {
        assertEquals(3, ReplayParserCli.run(new String[] {"--input", tempDir.resolve("missing.dem").toString()}));
    }

    @Test
    void acceptsDebugDiscoveryFlag() throws IOException {
        Path replay = tempDir.resolve("debug.dem");
        Path output = tempDir.resolve("debug-artifact.json");
        Files.writeString(replay, "demo");

        int code = ReplayParserCli.run(new String[] {"--input", replay.toString(), "--output", output.toString(), "--debug-discovery"});

        assertEquals(0, code);
        String json = Files.readString(output);
        assertTrue(json.contains("debug_discovery"));
        assertTrue(json.contains("first_bytes_hex"));
    }

    @Test
    void writesSchemaValidJsonToOutputFile() throws IOException {
        Path replay = tempDir.resolve("match.dem");
        Path output = tempDir.resolve("artifact.json");
        Files.writeString(replay, "demo");

        int code = ReplayParserCli.run(new String[] {"--input", replay.toString(), "--output", output.toString(), "--pretty"});

        assertEquals(0, code);
        String json = Files.readString(output);
        assertTrue(json.contains("deadlock-replay-parse-v1"));
        assertTrue(json.contains("warnings"));
    }
}
