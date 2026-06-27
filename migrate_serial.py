#!/usr/bin/env python3
"""
migrate_serial.py - Einmalige Migration: Standorte auf stabile Serial-Identitaet.

Was es tut:
  1. Holt die Geraeteliste aus RMS (Name -> Seriennummer) - oder aus --from-json.
  2. Traegt fuer jeden Standort OHNE 'serial' die passende Seriennummer in
     standorte.yaml nach (Match ueber den aktuellen Namen).
  3. Benennt vorhandene Schluessel  out/keys/<name>.<pfad>.{priv,pub}
     um in  out/keys/<serial>.<pfad>.{priv,pub}  -> die WireGuard-Identitaet
     bleibt 1:1 erhalten (KEIN Neu-Schluesseln, kein Tunnel-Bruch).

Sicherheit:
  * STANDARD ist ein PROBELAUF (zeigt nur, was passieren wuerde).
  * Erst mit  --apply  wird wirklich geaendert; vorher legt es ein Backup an.
  * Schluessel werden nur UMBENANNT (nie geloescht), und nie ueberschrieben.

Aufruf (auf dem Anker, mit Master fuer den Token):
  cd /opt/feldnetz
  sudo FELDNETZ_MASTER='...' .venv/bin/python3 migrate_serial.py            # Probelauf
  sudo FELDNETZ_MASTER='...' .venv/bin/python3 migrate_serial.py --apply    # scharf
  # Alternativ ohne Token, mit vorab gespeicherter Geraeteliste:
  #   .venv/bin/python3 push_rms.py --discover-json > devs.json   (mit Master)
  #   .venv/bin/python3 migrate_serial.py --from-json devs.json [--apply]
"""
import argparse
import json
import os
import shutil
import sys
import time

try:
    import yaml
except ImportError:
    sys.exit("PyYAML fehlt: pip install pyyaml")

HERE = os.path.dirname(os.path.abspath(__file__))
YAML = os.path.join(HERE, "standorte.yaml")
KEYS = os.path.join(HERE, "out", "keys")


def load_devices(from_json):
    if from_json:
        data = json.load(open(from_json, encoding="utf-8"))
        # akzeptiert sowohl [{name,serial,...}] als auch {"data":[...]}
        return data.get("data", data) if isinstance(data, dict) else data
    # ueber RMS-Token (nutzt push_rms + keystore)
    sys.path.insert(0, HERE)
    import push_rms
    return push_rms.fetch_devices(push_rms.get_token())


def key_files_for(name):
    """Vorhandene Schluesseldateien eines Standorts (Prefix '<name>.')."""
    if not os.path.isdir(KEYS):
        return []
    pre = f"{name}."
    return [f for f in os.listdir(KEYS)
            if f.startswith(pre) and (f.endswith(".priv") or f.endswith(".pub"))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="scharf (sonst Probelauf)")
    ap.add_argument("--from-json", help="Geraeteliste aus Datei statt RMS")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(YAML, encoding="utf-8"))
    sites = cfg.get("sites", []) or []
    devs = load_devices(args.from_json)
    by_name = {str(d.get("name", "")).lower(): d for d in devs}

    print(f"{'Standort':28} {'Serial':12} Aktion")
    print("-" * 70)
    serial_sets = []     # (site, serial)
    renames = []         # (old_path, new_path)
    problems = []

    for s in sites:
        name = str(s.get("name", ""))
        if str(s.get("serial") or "").strip():
            print(f"{name:28} {str(s['serial']):12} schon gesetzt - uebersprungen")
            continue
        d = by_name.get(name.lower())
        if not d:
            problems.append(f"{name}: kein RMS-Geraet mit diesem Namen gefunden")
            print(f"{name:28} {'-':12} KEIN RMS-MATCH")
            continue
        ser = str(d.get("serial") or "").strip()
        if not ser:
            problems.append(f"{name}: RMS-Geraet hat keine Seriennummer")
            print(f"{name:28} {'-':12} RMS OHNE SERIAL")
            continue
        serial_sets.append((s, ser))
        # Schluessel umbenennen <name>.* -> <serial>.*
        ren_here = []
        for f in key_files_for(name):
            new = ser + f[len(name):]          # ersetzt nur den Namens-Prefix
            old_p = os.path.join(KEYS, f)
            new_p = os.path.join(KEYS, new)
            if os.path.exists(new_p):
                problems.append(f"{name}: Ziel {new} existiert schon - Rename uebersprungen")
                continue
            renames.append((old_p, new_p))
            ren_here.append(f"{f} -> {new}")
        keys_info = (", ".join(ren_here) if ren_here else "keine Schluesseldateien")
        print(f"{name:28} {ser:12} serial setzen; Keys: {keys_info}")

    print("\nZusammenfassung:")
    print(f"  {len(serial_sets)} Standorte bekommen eine Serial")
    print(f"  {len(renames)} Schluesseldateien werden umbenannt")
    if problems:
        print("  Hinweise/Probleme:")
        for p in problems:
            print(f"    - {p}")

    if not args.apply:
        print("\nPROBELAUF - es wurde NICHTS geaendert. Scharf mit  --apply")
        return

    # --- scharf: Backup, dann anwenden ---
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bdir = os.path.join(HERE, f"backup-migrate-{stamp}")
    os.makedirs(bdir, exist_ok=True)
    shutil.copy2(YAML, os.path.join(bdir, "standorte.yaml"))
    if os.path.isdir(KEYS):
        shutil.copytree(KEYS, os.path.join(bdir, "keys"))
    print(f"\nBackup angelegt: {bdir}")

    for old_p, new_p in renames:
        os.rename(old_p, new_p)
    for s, ser in serial_sets:
        s["serial"] = ser
    with open(YAML, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)

    print(f"Fertig: {len(serial_sets)} Serials gesetzt, {len(renames)} Keys umbenannt.")
    print("Naechster Schritt: generate.py -> out/devices vergleichen (muss identisch bleiben).")


if __name__ == "__main__":
    main()
