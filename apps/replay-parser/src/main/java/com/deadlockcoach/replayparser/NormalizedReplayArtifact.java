package com.deadlockcoach.replayparser;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.Map;

public record NormalizedReplayArtifact(
        @JsonProperty("schema_version") String schemaVersion,
        Map<String, Object> parser,
        Map<String, Object> source,
        Map<String, Object> match,
        List<Map<String, Object>> players,
        List<Map<String, Object>> timeline,
        Map<String, Object> capabilities,
        List<String> warnings,
        Map<String, Object> stats) {}
