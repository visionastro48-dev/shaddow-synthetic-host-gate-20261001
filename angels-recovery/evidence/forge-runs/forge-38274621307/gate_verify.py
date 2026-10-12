import json
import sys

def main():
    # Check if exactly one argument is provided
    if len(sys.argv) != 2:
        print("BLOCKED")
        sys.exit(2)

    json_filename = sys.argv[1]

    # Try to open and read the JSON file
    try:
        with open(json_filename, 'r') as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        print("BLOCKED")
        sys.exit(2)

    # Check if data is a dictionary
    if not isinstance(data, dict):
        print("BLOCKED")
        sys.exit(2)

    # Check if the set of keys matches exactly
    required_keys = {'production_authority_enabled', 'external_side_effects_enabled', 'legacy_job_replay_enabled'}
    if set(data.keys()) != required_keys:
        print("BLOCKED")
        sys.exit(2)

    # Check if each value is of type bool and equals False
    for key in required_keys:
        if not isinstance(data[key], bool) or data[key] != False:
            print("BLOCKED")
            sys.exit( 2 )

    # If all checks pass
    print("FAIL_CLOSED_OK")
    sys.exit(0)

if __name__ == "__main__":
    main()