#!/usr/bin/env python3
"""
wg_monitor.py - liefert WireGuard-Peer-Daten fuer Zabbix.

Aufrufe:
  wg_monitor.py discover [anker]   -> LLD-JSON aller Peers (Name + Pubkey)
  wg_monitor.py age <pubkey> [anker] -> Sekunden seit letztem Handshake
                                        (9999999 wenn nie verbunden)

Namen kommen aus out/hub/<anker>.peers.conf (Kommentar # NAME - LAN ...).
"""
import json, re, subprocess, sys, time

BASE = "/opt/feldnetz"

def names_map(anker):
    names = {}
    cur = None
    try:
        with open(f"{BASE}/out/hub/{anker}.peers.conf") as f:
            for line in f:
                m = re.match(r'^#\s*(\S+)\s*-\s*LAN', line)
                if m: cur = m.group(1)
                m = re.match(r'^PublicKey\s*=\s*(.+?)\s*$', line)
                if m and cur: names[m.group(1)] = cur
    except FileNotFoundError:
        pass
    return names

def wg_dump(anker):
    out = subprocess.run(["wg", "show", f"wg-{anker}", "dump"],
                         capture_output=True, text=True)
    peers = []
    for line in out.stdout.strip().splitlines()[1:]:  # 1. Zeile = Interface
        f = line.split("\t")
        if len(f) >= 5:
            peers.append({"pubkey": f[0], "handshake": int(f[4])})
    return peers

def cmd_discover(anker):
    names = names_map(anker)
    data = [{"{#PEER}": names.get(p["pubkey"], p["pubkey"][:12]),
             "{#PUBKEY}": p["pubkey"]} for p in wg_dump(anker)]
    print(json.dumps({"data": data}))

def cmd_age(pubkey, anker):
    now = int(time.time())
    for p in wg_dump(anker):
        if p["pubkey"] == pubkey:
            print(9999999 if p["handshake"] == 0 else now - p["handshake"])
            return
    print(9999999)  # Peer nicht gefunden = wie nie verbunden

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Aufruf: wg_monitor.py discover|age <pubkey> [anker]")
    mode = sys.argv[1]
    if mode == "discover":
        cmd_discover(sys.argv[2] if len(sys.argv) > 2 else "a1")
    elif mode == "age":
        cmd_age(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "a1")
