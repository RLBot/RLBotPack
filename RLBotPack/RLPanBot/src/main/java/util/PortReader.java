package util;

import java.util.Optional;

/**
 * Utility for reading a network port out of a command line arguments.
 *
 * This class is here for your convenience, it is NOT part of the framework. You can add to it as much
 * as you want, or delete it.
 */
public class PortReader {

    public static Optional<Integer> readPortFromArgs(String[] args) {
        if (args.length == 0) {
            return Optional.empty();
        }
        try {
            return Optional.of(Integer.parseInt(args[0]));
        } catch (NumberFormatException e) {
            return Optional.empty();
        }
    }
}
