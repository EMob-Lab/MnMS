#!/bin/sh

set -e

# Check that the given input file exists, and if not, print an error message and exit.
# REMARKS:
# - This check is meant to provide an error message that highlights the possible error causes that are
#   specific to the Docker-based MnMS set-up. The requirements for the input file in the current directory
#   and relative paths do not exist if MnMS is used without Docker.
# - The same requirements apply for the auxiliary input files referenced in the JSON config file
#   or in the Python run file, if any. But we cannot check them here...
check_input_file() {
    if [ -e "$1" ]; then
        return
    fi
    printf "Error: input file '%s' not found.\n" "$1" >&2
    echo "Note: the input file must be located in the current directory (or one of its subdirectories)," >&2
    echo "and referenced by a relative path." >&2
    exit 2
}

# If no argument (or "--help" or similar) is provided, print usage information and exit.
if [ $# -eq 0 ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    cat /app/entrypoint-usage.txt
    exit 0
fi

# Otherwise, depending on the first argument...
case "$1" in

    # For a JSON file, run the MnMS CLI launcher.
    *.[jJ][sS][oO][nN])
        check_input_file "$1"
        exec mnms "$@"
        ;;

    # For a Python file (more advanced usage), run it directly.
    *.[pP][yY])
        check_input_file "$1"
        exec python "$@"
        ;;

    # Other file types are not supported.
    *)
        printf "Error: unsupported argument '%s' (expected a .json or .py file).\n" "$1" >&2
        echo "" >&2
        cat /app/entrypoint-usage.txt >&2
        exit 2
        ;;

esac
