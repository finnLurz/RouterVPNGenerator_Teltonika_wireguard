#!/usr/bin/env python3
"""Schreibt aus entschluesselter YAML (stdin) die out/keys/*.priv zurueck."""
import os, sys, yaml
KEYS = os.path.join(os.path.dirname(__file__), "..", "out", "keys")
os.makedirs(KEYS, exist_ok=True)
data = yaml.safe_load(sys.stdin) or {}
for fn, content in data.items():
    p = os.path.join(KEYS, fn)
    open(p, "w").write(content + "\n")
    os.chmod(p, 0o600)
    # passenden .pub aus .priv ableiten
    if fn.endswith(".priv"):
        import subprocess
        pub = subprocess.run(["wg","pubkey"], input=content, capture_output=True, text=True).stdout.strip()
        open(p[:-5]+".pub","w").write(pub+"\n")
print(f"{len(data)} Schluessel wiederhergestellt.", file=sys.stderr)
