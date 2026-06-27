#!/usr/bin/env python3
"""
netplan.py - Netzplanungs-Engine (eine Wahrheit fuer CLI, Web und Generator).

Aufgaben:
  * Subnetz-Mathematik: aus "Geraete pro Router" bzw. "Anzahl Router" die
    optimale Praefixlaenge / Supernetz-Groesse vorschlagen - mit Klartext.
  * Pool-Verwaltung: benannte Netz-Pools (Sirenen, Fahrzeuge, Messstellen, ...)
    aus standorte.yaml lesen und Standort-Subnetze ueberlappungsfrei vergeben.

Bewusst ohne Fremd-Abhaengigkeiten ausser PyYAML, damit ueberall nutzbar.
"""
import ipaddress
import math

# Kleinste sinnvolle Standort-Maske: /30 = 2 nutzbare Hosts (Gateway + 1 Geraet).
MIN_HOST_PREFIX = 30
# /24 als kleinste Praefixzahl (= groesstes Einzelnetz), darunter wird es unueblich.
MAX_HOST_PREFIX = 24


def usable_hosts(prefix):
    """Nutzbare Hosts in einem IPv4-Netz mit gegebener Praefixlaenge."""
    prefix = int(prefix)
    if prefix >= 31:
        return max(0, 2 ** (32 - prefix) - 0)  # /31,/32: Sonderfaelle, hier ohne -2
    return 2 ** (32 - prefix) - 2  # Netz- und Broadcast-Adresse abziehen


def suggest_host_prefix(devices_per_router):
    """Kleinstes Netz (groesste Praefixzahl), das Gateway + N Endgeraete fasst.

    Rueckgabe: dict mit prefix, usable, reserve, erklaerung.
    """
    n = max(1, int(devices_per_router))
    needed = n + 1  # +1 fuer das Router-LAN-Gateway
    # Vom kleinsten Netz (/30) aufwaerts zum groessten (/24) suchen und das
    # erste nehmen, das gross genug ist -> kleinstes passendes Netz.
    for prefix in range(MIN_HOST_PREFIX, MAX_HOST_PREFIX - 1, -1):
        if usable_hosts(prefix) >= needed:
            u = usable_hosts(prefix)
            return {
                "host_prefix": prefix,
                "usable": u,
                "needed": needed,
                "reserve": u - needed,
                "explain": (
                    f"/{prefix} bietet {u} nutzbare Adressen. Benoetigt: {n} Geraete "
                    f"+ 1 Gateway = {needed}. Reserve: {u - needed}."
                ),
            }
    # mehr Geraete als ein /24 fasst -> /24 zurueck, mit Warnung
    u = usable_hosts(MAX_HOST_PREFIX)
    return {
        "host_prefix": MAX_HOST_PREFIX,
        "usable": u,
        "needed": needed,
        "reserve": u - needed,
        "explain": (
            f"Achtung: {n} Geraete passen nicht in ein einzelnes /{MAX_HOST_PREFIX} "
            f"({u} nutzbar). Pool/Architektur ueberdenken."
        ),
    }


def suggest_supernet_prefix(num_routers, host_prefix):
    """Welche Supernetz-Groesse fasst num_routers Subnetze der Groesse host_prefix?

    Rueckgabe: dict mit supernet_prefix, capacity, erklaerung.
    """
    routers = max(1, int(num_routers))
    host_prefix = int(host_prefix)
    bits = math.ceil(math.log2(routers))  # benoetigte Subnetz-Bits
    supernet_prefix = host_prefix - bits
    if supernet_prefix < 0:
        supernet_prefix = 0
    capacity = 2 ** (host_prefix - supernet_prefix)
    return {
        "supernet_prefix": supernet_prefix,
        "capacity": capacity,
        "requested": routers,
        "host_prefix": host_prefix,
        "explain": (
            f"/{supernet_prefix} fasst {capacity} Subnetze der Groesse /{host_prefix} "
            f"(angefragt: {routers}). Reserve: {capacity - routers} Standorte."
        ),
    }


def plan_pool(num_routers, devices_per_router=None, host_prefix=None):
    """Kompletter Vorschlag fuer einen neuen Pool.

    Genau EINE der beiden Angaben reicht:
      * devices_per_router -> host_prefix wird berechnet
      * host_prefix        -> direkt verwendet
    """
    if host_prefix is None:
        if devices_per_router is None:
            raise ValueError("devices_per_router oder host_prefix angeben.")
        hp = suggest_host_prefix(devices_per_router)
    else:
        hp = {
            "host_prefix": int(host_prefix),
            "usable": usable_hosts(host_prefix),
            "needed": None,
            "reserve": None,
            "explain": f"/{int(host_prefix)} fest vorgegeben "
                       f"({usable_hosts(host_prefix)} nutzbare Adressen).",
        }
    sn = suggest_supernet_prefix(num_routers, hp["host_prefix"])
    return {"host": hp, "supernet": sn}


# --------------------------------------------------------------------------- #
#  Pool-Modell aus standorte.yaml
# --------------------------------------------------------------------------- #

DEFAULT_POOLS = [
    {"name": "sirene", "label": "Sirenen", "profile": "sirene",
     "supernet": "192.168.80.0/24", "host_prefix": 28, "index_start": 11,
     "advertise": True},
    {"name": "fahrzeug", "label": "Fahrzeuge", "profile": "fahrzeug",
     "supernet": "192.168.81.0/24", "host_prefix": 27, "index_start": 31,
     "advertise": True},
]


def get_pools(cfg):
    """Liefert die Pool-Liste. Faellt auf das alte Hardcode-Verhalten zurueck,
    wenn keine address_plan.pools vorhanden sind (Rueckwaertskompatibilitaet)."""
    plan = (cfg or {}).get("address_plan") or {}
    pools = plan.get("pools")
    if pools:
        return pools
    return [dict(p) for p in DEFAULT_POOLS]


def pool_by_name(cfg, name):
    for p in get_pools(cfg):
        if p.get("name") == name:
            return p
    return None


def pool_slots(pool):
    """Alle moeglichen Standort-Subnetze eines Pools (als ip_network-Liste)."""
    sn = ipaddress.ip_network(pool["supernet"], strict=True)
    return list(sn.subnets(new_prefix=int(pool["host_prefix"])))


def allocate(cfg, sites):
    """Vergibt site_index und lan_subnet pro Standort gemaess seinem Pool.

    Ein Standort waehlt seinen Pool ueber das Feld 'pool' oder - kompatibel -
    ueber 'profile' (Profilname == Poolname). Bereits gesetzte Werte bleiben.
    Gibt (sites, fehlerliste) zurueck.
    """
    errs = []
    used_idx = {int(s["site_index"]) for s in sites
                if str(s.get("site_index", "")).strip()}
    used_net = {str(s.get("lan_subnet", "")).strip() for s in sites
                if str(s.get("lan_subnet", "")).strip()}

    # je Pool einen laufenden Index- und Slot-Zeiger
    pools = {p["name"]: p for p in get_pools(cfg)}
    idx_ptr = {name: int(p.get("index_start", 11)) for name, p in pools.items()}
    slot_ptr = {name: 0 for name in pools}
    slots = {name: pool_slots(p) for name, p in pools.items()}

    for s in sites:
        pname = s.get("pool") or s.get("profile")
        if pname not in pools:
            errs.append(f"{s.get('name','?')}: unbekannter Pool/Profil '{pname}'.")
            continue
        # site_index
        if not str(s.get("site_index", "")).strip():
            ip = idx_ptr[pname]
            while ip in used_idx:
                ip += 1
            s["site_index"] = ip
            used_idx.add(ip)
            idx_ptr[pname] = ip + 1
        else:
            s["site_index"] = int(s["site_index"])
        # lan_subnet
        if not str(s.get("lan_subnet", "")).strip():
            pool_slots_list = slots[pname]
            ptr = slot_ptr[pname]
            while ptr < len(pool_slots_list) and str(pool_slots_list[ptr]) in used_net:
                ptr += 1
            if ptr >= len(pool_slots_list):
                errs.append(f"{s.get('name','?')}: Pool '{pname}' ist voll "
                            f"({pools[pname]['supernet']} /{pools[pname]['host_prefix']}).")
                continue
            s["lan_subnet"] = str(pool_slots_list[ptr])
            used_net.add(s["lan_subnet"])
            slot_ptr[pname] = ptr + 1
    return sites, errs


if __name__ == "__main__":
    # Selbsttest / Demonstration
    print("== Geraete pro Router -> Standort-Maske ==")
    for n in (1, 5, 12, 13, 30, 60, 300):
        r = suggest_host_prefix(n)
        print(f"{n:>4} Geraete -> /{r['host_prefix']}  ({r['usable']} nutzbar)")
    print("\n== Anzahl Router -> Supernetz ==")
    for n in (2, 10, 17, 50, 200):
        r = suggest_supernet_prefix(n, 28)
        print(f"{n:>4} Router (/28) -> Supernetz /{r['supernet_prefix']} "
              f"({r['capacity']} Plaetze)")
    print("\n== Kompletter Pool-Vorschlag: 17 Router, 8 Geraete/Router ==")
    p = plan_pool(17, devices_per_router=8)
    print(" ", p["host"]["explain"])
    print(" ", p["supernet"]["explain"])
