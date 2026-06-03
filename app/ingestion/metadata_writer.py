import json


def save_metadata(metadata, output_path):
    with open(output_path, "w") as f:
        json.dump(metadata, f, indent=4)
