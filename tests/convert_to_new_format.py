#!/usr/bin/env python3

import sys
from pathlib import Path

import superannotate as sa

if __name__ == "__main__":
    input_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    project_type = sys.argv[3]

    all_jsons = input_dir.rglob(
        "*___objects.json" if project_type == "Vector" else "*___pixel.json"
    )

    for json_path in all_jsons:
        new_json_path = output_dir / json_path.relative_to(input_dir)
        print("Updating", json_path, "to new JSON", new_json_path)
        sa.update_json_format(json_path, new_json_path, project_type)
