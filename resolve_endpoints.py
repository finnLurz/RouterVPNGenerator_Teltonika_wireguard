#!/usr/bin/env python3
"""
resolve_endpoints.py - prueft/aktualisiert die Anker-Endpunkte.

Pro Anker kann endpoint_host eine feste IP ODER ein DNS-Name sein:
  - Feste IP        -> wird unveraendert verwendet.
  - DNS-Name        -> Modus waehlbar:
      * 'name'  : Name bleibt in der Config (RUTs loesen selbst auf, wie Netmaker)
      * 'ip'    : Name wird jetzt zu IP aufgeloest und als IP eingsetzt

Steuerung pro Anker ueber optionales Feld 'endpoint_mode' (name|ip) in der YAML.
Default: feste IP -> 'ip', DNS-Name -> 'name' (selbst aufloesen).

Aufruf:
  python3 resolve_endpoints.py --check     # nur anzeigen, ob/where Namen aufloesen
  python3 resolve_endpoints.py --write      # bei Modus 'ip' die IP in die YAML schreiben
"""
import argparse
import ipaddress
import os
import socket
import sys

try:
    import yaml
except ImportError:
    sys.exit("pip install pyyaml")

HERE = os.path.dirname(os.path.abspath(__file__))
YAML = os.path.join(HERE, "standorte.yaml")


def is_ip(s):
    try:
        ipaddress.ip_address(s)
        return True
    except ValueError:
        return False


def resolve(name):
    try:
        infos = socket.getaddrinfo(name, None, socket.AF_INET)
        return sorted({i[4][0] for i in infos})
    except socket.gaierror as e:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="nur anzeigen")
    ap.add_argument("--write", action="store_true", help="aufgeloeste IPs (Modus ip) schreiben")
    args = ap.parse_args()
    if not (args.check or args.write):
        args.check = True

    cfg = yaml.safe_load(open(YAML))
    changed = 0
    print(f"{'Anker':6} {'Modus':6} {'Endpunkt':28} Aufloesung")
    print("-" * 70)
    for a in cfg["anchors"]:
        host = str(a.get("endpoint_host", "")).strip()
        mode = a.get("endpoint_mode") or ("ip" if is_ip(host) else "name")
        if is_ip(host):
            print(f"{a['id']:6} {'(ip)':6} {host:28} feste IP")
            continue
        ips = resolve(host)
        if ips is None:
            status = "!! loest NICHT auf (nginx/DNS pruefen)"
        else:
            status = ", ".join(ips)
        print(f"{a['id']:6} {mode:6} {host:28} {status}")
        if args.write and mode == "ip" and ips:
            # bei Modus 'ip': ersten A-Record als endpoint einsetzen, Name merken
            a["endpoint_host_dns"] = host
            a["endpoint_host"] = ips[0]
            changed += 1

    if args.write and changed:
        yaml.safe_dump(cfg, open(YAML, "w"), allow_unicode=True, sort_keys=False)
        print(f"\n{changed} Anker auf aufgeloeste IP gesetzt (Original-Name in endpoint_host_dns).")
    elif args.check:
        print("\nNur Anzeige. Mit --write werden Modus-'ip'-Namen zu IPs aufgeloest.")
        print("Tipp: Modus 'name' (Default bei DNS) laesst die RUTs selbst aufloesen -")
        print("      dann genuegt ein Eintrag im nginx/DNS, ohne Neugenerierung.")


if __name__ == "__main__":
    main()
