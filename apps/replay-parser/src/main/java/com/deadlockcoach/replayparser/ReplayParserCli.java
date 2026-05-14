package com.deadlockcoach.replayparser;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

public final class ReplayParserCli {
    private ReplayParserCli() {}

    public static void main(String[] args) {
        int code = run(args);
        if (code != 0) {
            System.exit(code);
        }
    }

    static int run(String[] args) {
        try {
            Options options = Options.parse(args);
            if (!Files.isReadable(options.input())) {
                throw new ReplayParserException(3, "input file is missing or unreadable");
            }
            NormalizedReplayArtifact artifact = new ClarityReplayParser().parse(options.input(), options.maxEvents(), options.debugDiscovery());
            ObjectMapper mapper = new ObjectMapper();
            if (options.pretty()) {
                mapper.enable(SerializationFeature.INDENT_OUTPUT);
            }
            String json = mapper.writeValueAsString(artifact);
            if (options.output() == null) {
                System.out.println(json);
            } else {
                Files.writeString(options.output(), json);
            }
            return 0;
        } catch (ReplayParserException exc) {
            System.err.println(exc.getMessage());
            return exc.exitCode();
        } catch (IOException exc) {
            System.err.println("failed to write parser output");
            return 11;
        }
    }

    record Options(Path input, Path output, boolean pretty, int maxEvents, boolean debugDiscovery) {
        static Options parse(String[] args) {
            Path input = null;
            Path output = null;
            boolean pretty = false;
            int maxEvents = 500;
            boolean debugDiscovery = false;
            for (int i = 0; i < args.length; i++) {
                switch (args[i]) {
                    case "--input" -> input = Path.of(requireValue(args, ++i, "--input"));
                    case "--output" -> output = Path.of(requireValue(args, ++i, "--output"));
                    case "--pretty" -> pretty = true;
                    case "--max-events" -> maxEvents = parseMaxEvents(requireValue(args, ++i, "--max-events"));
                    case "--debug-discovery" -> debugDiscovery = true;
                    default -> throw new ReplayParserException(2, "unknown argument: " + args[i]);
                }
            }
            if (input == null) {
                throw new ReplayParserException(2, "--input is required");
            }
            return new Options(input, output, pretty, maxEvents, debugDiscovery);
        }

        private static String requireValue(String[] args, int index, String flag) {
            if (index >= args.length || args[index].startsWith("--")) {
                throw new ReplayParserException(2, flag + " requires a value");
            }
            return args[index];
        }

        private static int parseMaxEvents(String value) {
            try {
                int parsed = Integer.parseInt(value);
                if (parsed < 0) {
                    throw new NumberFormatException("negative");
                }
                return parsed;
            } catch (NumberFormatException exc) {
                throw new ReplayParserException(2, "--max-events must be a non-negative integer");
            }
        }
    }
}
