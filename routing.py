#!/usr/bin/env python3
"""
routing.py - erzeugt aus standorte.yaml eine FRR-Konfiguration (BGP und/oder OSPF).

Designprinzip (wie im Watchdog-Konzept): Der Watchdog setzt pro lebendem Tunnel
das jeweilige Standort-/28 als Kernel-Route. FRR verteilt NUR diese lebenden
Routen (redistribute kernel) - gefiltert auf die konfigurierten Pool-Supernetze.
So wird nie ein totes Netz annonciert (kein Blackhole).

Aufruf:
  python3 routing.py            -> schreibt out/anker/frr.conf + gibt sie aus
"""
import os
import sys

try:
    import yaml
except ImportError:
    sys.exit("PyYAML fehlt: pip install pyyaml")

import netplan

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_ANKER = os.path.join(HERE, "out", "anker")


def advertised_supernets(cfg):
    """Pool-Supernetze, die ins Routing sollen (advertise: true)."""
    return [p["supernet"] for p in netplan.get_pools(cfg) if p.get("advertise", True)]


def frr_config(cfg):
    r = cfg.get("routing") or {}
    proto = (r.get("protocol") or "bgp").lower()
    rid = r.get("router_id", "")
    supernets = advertised_supernets(cfg)

    L = ["! FRR-Konfiguration - GENERIERT von routing.py, nicht von Hand aendern.",
         "! Verteilt die vom Watchdog gesetzten Standort-Routen (lebende Tunnel).",
         f"! Protokoll: {proto}", "!"]

    if proto == "none":
        L.append("! routing.protocol = none -> kein dynamisches Routing konfiguriert.")
        return "\n".join(L) + "\n"

    # Filter: nur Subnetze innerhalb der Feldnetz-Supernetze nach aussen geben.
    for i, sn in enumerate(supernets, start=1):
        L.append(f"ip prefix-list FELDNETZ seq {i*5} permit {sn} le 32")
    L += ["!",
          "route-map FELDNETZ-OUT permit 10",
          " match ip address prefix-list FELDNETZ",
          "!"]

    if proto in ("bgp", "both"):
        b = r.get("bgp") or {}
        L.append(f"router bgp {b.get('local_as', '<LOCAL_AS>')}")
        if rid:
            L.append(f" bgp router-id {rid}")
        L.append(" no bgp ebgp-requires-policy")
        neighbors = b.get("neighbors") or []
        for nb in neighbors:
            L.append(f" neighbor {nb['ip']} remote-as {nb['remote_as']}")
            if nb.get("description"):
                L.append(f" neighbor {nb['ip']} description {nb['description']}")
        L.append(" address-family ipv4 unicast")
        L.append("  redistribute kernel route-map FELDNETZ-OUT")
        for nb in neighbors:
            L.append(f"  neighbor {nb['ip']} activate")
        L += [" exit-address-family", "!"]

    if proto in ("ospf", "both"):
        o = r.get("ospf") or {}
        L.append("router ospf")
        if rid:
            L.append(f" ospf router-id {rid}")
        # Lebende Standort-Routen als externe OSPF-Routen verteilen (gefiltert).
        L.append(" redistribute kernel route-map FELDNETZ-OUT")
        L.append("!")

    return "\n".join(L) + "\n"


def write(cfg):
    os.makedirs(OUT_ANKER, exist_ok=True)
    txt = frr_config(cfg)
    with open(os.path.join(OUT_ANKER, "frr.conf"), "w", encoding="utf-8") as f:
        f.write(txt)
    return txt


def main():
    with open(os.path.join(HERE, "standorte.yaml"), encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    txt = write(cfg)
    print(txt)
    print("-> out/anker/frr.conf geschrieben.")


if __name__ == "__main__":
    main()
