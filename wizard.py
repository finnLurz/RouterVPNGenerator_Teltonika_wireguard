#!/usr/bin/env python3
"""
wizard.py - Netz-Assistent (Terminal).

Fuehrt Schritt fuer Schritt durch:
  1) Subnetz-Rechner       - "Wie gross muss mein Netz sein?"
  2) Neues Netz anlegen    - benannten Pool erzeugen, Maske/Supernetz wird
                             automatisch vorgeschlagen (nach Routern ODER
                             Geraeten pro Router)
  3) Standort hinzufuegen  - Router einem Pool zuordnen, IP wird automatisch vergeben
  4) Routing anzeigen      - generierte FRR-Konfiguration zeigen

Schreibt direkt in standorte.yaml. Danach wie gewohnt:  python3 generate.py
"""
import ipaddress
import os
import sys

try:
    import yaml
except ImportError:
    sys.exit("PyYAML fehlt: pip install pyyaml")

import netplan
import routing

HERE = os.path.dirname(os.path.abspath(__file__))
YAML = os.path.join(HERE, "standorte.yaml")


def load():
    with open(YAML, encoding="utf-8") as f:
        return yaml.safe_load(f)


def save(cfg):
    with open(YAML, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)


def ask(prompt, default=None):
    suffix = f" [{default}]" if default is not None else ""
    val = input(f"{prompt}{suffix}: ").strip()
    return val or (str(default) if default is not None else "")


def ask_int(prompt, default=None, lo=1, hi=10_000):
    while True:
        raw = ask(prompt, default)
        try:
            v = int(raw)
            if lo <= v <= hi:
                return v
        except ValueError:
            pass
        print(f"  Bitte eine Zahl zwischen {lo} und {hi} eingeben.")


# --------------------------------------------------------------------------- #

def calc_flow():
    """Reiner Rechner - aendert nichts."""
    print("\n-- Subnetz-Rechner --")
    print("Wie soll die Groesse bestimmt werden?")
    print("  [1] Ich kenne die Zahl der Endgeraete pro Router")
    print("  [2] Ich gebe die Maske direkt vor (/28, /27, ...)")
    mode = ask("Auswahl", "1")
    if mode == "2":
        hp = ask_int("Maske (Praefixzahl, z.B. 28)", 28, 24, 30)
        host = {"host_prefix": hp, "usable": netplan.usable_hosts(hp),
                "explain": f"/{hp} = {netplan.usable_hosts(hp)} nutzbare Adressen."}
    else:
        dev = ask_int("Endgeraete pro Router", 10)
        host = netplan.suggest_host_prefix(dev)
    routers = ask_int("Wie viele Router (Standorte) sollen rein?", 17)
    sn = netplan.suggest_supernet_prefix(routers, host["host_prefix"])
    print("\nVorschlag:")
    print("  Standort-Maske:", f"/{host['host_prefix']}  ", host["explain"])
    print("  Supernetz:     ", f"/{sn['supernet_prefix']}  ", sn["explain"])
    return host, sn, routers


def overlaps_existing(cfg, net):
    nets = []
    for p in netplan.get_pools(cfg):
        nets.append(ipaddress.ip_network(p["supernet"]))
    for r in (cfg.get("global", {}).get("routes_central") or []):
        try:
            nets.append(ipaddress.ip_network(r))
        except ValueError:
            pass
    return [str(x) for x in nets if net.overlaps(x)]


def new_pool_flow(cfg):
    print("\n-- Neues Netz (Pool) anlegen --")
    name = ask("Kurzname (technisch, z.B. messstellen)")
    if not name:
        print("Abgebrochen."); return
    if netplan.pool_by_name(cfg, name):
        print(f"Pool '{name}' existiert bereits."); return
    label = ask("Anzeigename", name.capitalize())
    host, sn, routers = calc_flow()
    # Basisadresse fuer das Supernetz erfragen
    while True:
        base = ask(f"Basis-Netz fuer diesen Pool als /{sn['supernet_prefix']} "
                   f"(z.B. 192.168.96.0/{sn['supernet_prefix']})")
        try:
            net = ipaddress.ip_network(base, strict=True)
        except ValueError as e:
            print(f"  Ungueltig: {e}"); continue
        if net.prefixlen != sn["supernet_prefix"]:
            print(f"  Hinweis: erwartet /{sn['supernet_prefix']}, bekommen "
                  f"/{net.prefixlen}. Passt die Groesse?")
        clash = overlaps_existing(cfg, net)
        if clash:
            print(f"  Ueberlappt mit: {', '.join(clash)} - bitte anderes Netz.")
            continue
        break
    # Geraeteverhalten (Profil) waehlen
    profs = list((cfg.get("profiles") or {}).keys()) or ["fahrzeug"]
    print("Geraeteverhalten (Profil) fuer diesen Pool:")
    for i, pr in enumerate(profs, 1):
        print(f"  [{i}] {pr}")
    pi = ask_int("Auswahl", 1, 1, len(profs))
    behavior = profs[pi - 1]
    idx_start = ask_int("Start fuer site_index dieses Pools", 100, 1, 254)
    advertise = ask("Ins Routing (BGP/OSPF) annoncieren? (j/n)", "j").lower().startswith("j")
    pool = {"name": name, "label": label, "profile": behavior, "supernet": str(net),
            "host_prefix": host["host_prefix"], "index_start": idx_start,
            "advertise": advertise}
    cfg.setdefault("address_plan", {}).setdefault("pools", [])
    cfg["address_plan"]["pools"].append(pool)
    save(cfg)
    print(f"\nOK: Pool '{name}' angelegt ({net}, /{host['host_prefix']} je Standort).")
    print("Tipp: Standorte mit Menuepunkt [3] hinzufuegen, dann python3 generate.py")


def add_site_flow(cfg):
    print("\n-- Standort hinzufuegen --")
    pools = netplan.get_pools(cfg)
    print("Verfuegbare Pools:")
    for i, p in enumerate(pools, 1):
        print(f"  [{i}] {p['name']} ({p.get('label','')}, {p['supernet']} /{p['host_prefix']})")
    sel = ask_int("Pool waehlen", 1, 1, len(pools))
    pname = pools[sel - 1]["name"]
    name = ask("Standort-Name (eindeutig)")
    if not name:
        print("Abgebrochen."); return
    sites = list(cfg.get("sites") or [])
    if any(str(s.get("name", "")).lower() == name.lower() for s in sites):
        print("Name existiert bereits."); return
    behavior = pools[sel - 1].get("profile", pname)
    sites.append({"name": name, "pool": pname, "profile": behavior})
    sites, errs = netplan.allocate(cfg, sites)
    if errs:
        print("Fehler:", "; ".join(errs)); return
    cfg["sites"] = sites
    save(cfg)
    new = sites[-1]
    print(f"OK: {new['name']} -> Pool {pname}, index {new['site_index']}, "
          f"Netz {new['lan_subnet']}")


def show_routing(cfg):
    print("\n-- Generierte FRR-Konfiguration --\n")
    print(routing.frr_config(cfg))


def main():
    cfg = load()
    actions = {"1": calc_flow, "2": new_pool_flow, "3": add_site_flow,
               "4": show_routing}
    while True:
        print("\n=== Netz-Assistent ===")
        print("  [1] Subnetz-Rechner (nur anzeigen)")
        print("  [2] Neues Netz / Pool anlegen")
        print("  [3] Standort hinzufuegen")
        print("  [4] Routing (FRR) anzeigen")
        print("  [q] Beenden")
        choice = ask("Auswahl", "q")
        if choice in ("q", "Q", ""):
            print("Tschuess. Naechster Schritt: python3 generate.py")
            return
        fn = actions.get(choice)
        if not fn:
            print("Unbekannte Auswahl."); continue
        # calc_flow braucht keine cfg-Aenderung
        if fn is calc_flow:
            fn()
        else:
            fn(cfg)
            cfg = load()  # nach Aenderung frisch laden


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nAbgebrochen.")
