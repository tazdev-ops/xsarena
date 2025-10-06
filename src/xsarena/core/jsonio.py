"""jsonio: lightweight loader that supports .json or .json.gz transparently."""

import gzip
import json
import os


def load_json_auto(path: str):
    gz = path + ".gz"
    if os.path.exists(gz):
        with gzip.open(gz, "rt", encoding="utf-8") as f:
            return json.load(f)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
