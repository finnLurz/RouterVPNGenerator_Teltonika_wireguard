#!/usr/bin/env python3
"""Buendelt out/keys/*.priv zu einer YAML (fuer SOPS-Verschluesselung)."""
import os, sys, yaml
KEYS = os.path.join(os.path.dirname(__file__), "..", "out", "keys")
data = {}
if os.path.isdir(KEYS):
    for f in sorted(os.listdir(KEYS)):
        if f.endswith(".priv"):
            data[f] = open(os.path.join(KEYS, f)).read().strip()
yaml.safe_dump(data, sys.stdout)
