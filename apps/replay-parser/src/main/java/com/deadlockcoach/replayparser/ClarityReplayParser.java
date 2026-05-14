package com.deadlockcoach.replayparser;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.time.Instant;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;

public final class ClarityReplayParser {
    public NormalizedReplayArtifact parse(Path input, int maxEvents) throws IOException {
        Instant started = Instant.now();
        long size = Files.size(input);
        String sha256 = sha256(input);
        long elapsed = Duration.between(started, Instant.now()).toMillis();
        return new NormalizedReplayArtifact(
                "deadlock-replay-parse-v1",
                Map.of("name", "clarity", "version", "not-wired", "app_parser_version", "0.1.0"),
                Map.of("filename", input.getFileName().toString(), "size_bytes", size, "sha256", sha256),
                Map.of("match_id", "", "duration_seconds", 0, "tick_count", 0, "winning_team", ""),
                List.of(),
                List.of(),
                Map.of("overview_available", false, "players_available", false, "combat_log_available", false, "entities_sampled", false),
                List.of("Clarity extraction is not wired yet; this is schema-valid placeholder output."),
                Map.of("parse_duration_ms", elapsed, "timeline_events_emitted", 0, "timeline_events_dropped", 0));
    }

    private String sha256(Path input) throws IOException {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] bytes = Files.readAllBytes(input);
            return HexFormat.of().formatHex(digest.digest(bytes));
        } catch (NoSuchAlgorithmException exc) {
            throw new ReplayParserException(11, "sha256 algorithm unavailable");
        }
    }
}
