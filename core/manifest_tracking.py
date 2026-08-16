"""
core/manifest_tracking.py — SHA-256 tracking of input files.

When a file is added to input/, record: filename, sha256, mtime timestamp,
file size in a manifest.json. If the same filename reappears with a different
hash, log a warning (returned as a list of messages).

Future-proofing (multi-client): every record carries a client_id so the manifest
can later be split per gym network without a schema rewrite. Current behaviour is
single-client under the DEFAULT_CLIENT_ID.
"""
import os
import json
import hashlib
from datetime import datetime

DEFAULT_MANIFEST = os.path.join(os.path.dirname(__file__), "..", "config", "input_manifest.json")
# Multi-client future-proofing: single-client today, schema already carries the field.
DEFAULT_CLIENT_ID = "ariel_a_street_mall"


def sha256_of_file(path, chunk=65536):
    """Return lowercase hex sha256 of a file's bytes."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            block = f.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def _load(manifest_path):
    if not os.path.exists(manifest_path):
        return {}
    try:
        data = json.load(open(manifest_path, encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def register_input(path, manifest_path=None):
    """
    Add/refresh one input file in the manifest.
    Returns (entry, warnings) where warnings notes if an existing filename's
    hash changed (i.e. the file was modified/replaced).
    """
    manifest_path = manifest_path or DEFAULT_MANIFEST
    if not os.path.exists(path):
        return None, [f"cannot register missing file: {path}"]
    digest = sha256_of_file(path)
    stat = os.stat(path)
    entry = {
        "client_id": DEFAULT_CLIENT_ID,
        "filename": os.path.basename(path),
        "path": os.path.abspath(path),
        "sha256": digest,
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "size": stat.st_size,
    }
    manifest = _load(manifest_path)
    warnings = []
    key = entry["path"]  # absolute path is unique; basename can collide across dirs
    prev = manifest.get(key)
    if prev and prev.get("sha256") != digest:
        warnings.append(
            f"input changed: {entry['filename']} ({key}) hash "
            f"{prev.get('sha256')[:12]}... -> {digest[:12]}... (was modified)"
        )
    manifest[key] = entry
    json.dump(manifest, open(manifest_path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    return entry, warnings