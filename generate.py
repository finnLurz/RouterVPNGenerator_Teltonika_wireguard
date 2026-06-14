#!/usr/bin/env python3
"""Feldnetz-Generator v2 - Muster A (Keys zentral) + UCI-Skripte fuer RMS."""
import csv, os, subprocess, sys
try:
    import yaml
except ImportError:
    sys.exit("PyYAML fehlt: pip install pyyaml")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out"); KEYS = os.path.join(OUT, "keys")

def load():
    with open(os.path.join(HERE, "standorte.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)

def active_anchors(cfg):
    return [a for a in cfg["anchors"] if a.get("active")]

def wg_keypair(site, aid):
    os.makedirs(KEYS, exist_ok=True)
    pv = os.path.join(KEYS, f"{site}.{aid}.priv"); pb = os.path.join(KEYS, f"{site}.{aid}.pub")
    if os.path.exists(pv) and os.path.exists(pb):
        return open(pv).read().strip(), open(pb).read().strip()
    priv = subprocess.run(["wg","genkey"], capture_output=True, text=True).stdout.strip()
    pub = subprocess.run(["wg","pubkey"], input=priv, capture_output=True, text=True).stdout.strip()
    open(pv,"w").write(priv+"\n"); os.chmod(pv,0o600); open(pb,"w").write(pub+"\n")
    return priv, pub

def tunnel_ip(cfg,a,s): return f"{cfg['global']['tunnel_net_prefix']}.{a['path_id']}.{s['site_index']}"
def hub_ip(cfg,a): return f"{cfg['global']['tunnel_net_prefix']}.{a['path_id']}.{cfg['global']['hub_host_octet']}"

def cidr_to_mask(bits):
    bits=int(bits); m=(0xffffffff>>(32-bits))<<(32-bits)
    return ".".join(str((m>>(8*i))&0xff) for i in (3,2,1,0))

def lan_gw(s):
    net,mask=s["lan_subnet"].split("/"); o=net.split(".")
    return f"{o[0]}.{o[1]}.{o[2]}.{int(o[3])+1}", mask

def device_uci(cfg,s,keys):
    g=cfg["global"]; anchors=active_anchors(cfg); gw,mask=lan_gw(s)
    prof=cfg["profiles"][s["profile"]]
    import ipaddress as _ip
    net=_ip.ip_network(s["lan_subnet"])
    is_sirene = bool(prof.get("keep_internal_lan"))
    # Service-IP (zentral eindeutig) = Netz + offset, zeigt per NAT auf service_target
    service_ip = str(net.network_address + prof.get("service_offset",2)) if is_sirene else None
    L=["#!/bin/sh", f"# === {s['name']} | {s['lan_subnet']} | {s['profile']} ===",
       "# Generiert (Muster A). Idempotent - via RMS ausfuehren.", "set -e",""]

    # --- M2M-Mobilfunk: APN setzen (Grundlage fuer alles) ---
    apn = g.get("apn", "wsim")
    L+=["# --- Mobilfunk (M2M-SIM): APN setzen ---",
        f"# Ohne korrekten APN keine Datenverbindung. APN='{apn}', keine Zugangsdaten.",
        f"uci set network.mob1s1a1.apn='{apn}'",
        "uci set network.mob1s1a1.auth='none'",
        "uci -q delete network.mob1s1a1.username || true",
        "uci -q delete network.mob1s1a1.password || true",
        "# zweite SIM (falls vorhanden) gleich konfigurieren - schadet nicht",
        f"uci -q set network.mob1s2a1.apn='{apn}' || true",
        "uci -q set network.mob1s2a1.auth='none' || true",
        ""]

    if is_sirene:
        keep=prof["keep_internal_lan"]; tgt=prof["service_target"]
        keep_net=_ip.ip_network(keep)
        L+=[f"# --- Sirene: internes LAN {keep} BLEIBT (Steuerung {tgt} unveraendert) ---",
            f"# Zentrale Service-IP {service_ip} wird per 1:1-NAT auf {tgt} uebersetzt.",
            "# (LAN-IP des RUT wird NICHT geaendert - Steuerung bleibt erreichbar)",
            "# LAN-Port explizit auf internem Netz sicherstellen:",
            f"uci set network.lan.ipaddr='{keep_net.network_address + 1}'",
            f"uci set network.lan.netmask='{cidr_to_mask(keep_net.prefixlen)}'",
            "uci set network.lan.proto='static'",
            ""]
    else:
        L+=["# --- Fahrzeug: LAN auf Standort-Subnetz (geroutet) ---",
            f"uci set network.lan.ipaddr='{gw}'",
            f"uci set network.lan.netmask='{cidr_to_mask(mask)}'",""]
    for a in anchors:
        ifn=f"wg_{a['id']}"; tip=tunnel_ip(cfg,a,s); priv=keys[(s['name'],a['id'])][0]
        allowed=[f"{hub_ip(cfg,a)}/32"]+g["routes_central"]
        L+=[f"# --- Pfad {a['id'].upper()}: {a['description']} ---",
            f"uci set network.{ifn}=interface", f"uci set network.{ifn}.proto='wireguard'", f"uci set network.{ifn}.disabled='0'",
            "uci set network.mob1s1a1.peerdns='0'",
            "uci set network.mob1s1a1.dns='9.9.9.9 149.112.112.112'",
            f"uci set network.{ifn}.private_key='{priv}'",
            f"uci -q delete network.{ifn}.addresses || true",
            f"uci add_list network.{ifn}.addresses='{tip}/32'","",
            f"uci -q delete network.peer_{a['id']} || true",
            f"uci set network.peer_{a['id']}=wireguard_{ifn}",
            f"uci set network.peer_{a['id']}.public_key='{a['hub_public_key']}'",
            f"uci set network.peer_{a['id']}.endpoint_host='{a['endpoint_host']}'",
            f"uci set network.peer_{a['id']}.endpoint_port='{a['endpoint_port']}'",
            f"uci set network.peer_{a['id']}.persistent_keepalive='{g['keepalive']}'",
            f"uci set network.peer_{a['id']}.route_allowed_ips='1'"]
        for net in allowed: L.append(f"uci add_list network.peer_{a['id']}.allowed_ips='{net}'")
        L.append("")
    # --- Sirene: 1:1-NAT  Service-IP -> interne Steuerung ---
    if is_sirene:
        tgt=prof["service_target"]
        L+=["# Zentral erreichbare Service-IP auf dem WG-Interface + DNAT auf Steuerung",
            f"# Erreiche {service_ip} zentral -> RUT leitet auf {tgt}",
            "uci -q delete firewall.sirene_dnat || true",
            "uci set firewall.sirene_dnat=redirect",
            "uci set firewall.sirene_dnat.name='SIRENE-SVC'",
            "uci set firewall.sirene_dnat.src='wg'",
            "uci set firewall.sirene_dnat.proto='all'",
            f"uci set firewall.sirene_dnat.dest_ip='{tgt}'",
            f"uci set firewall.sirene_dnat.src_dip='{service_ip}'",
            "uci set firewall.sirene_dnat.target='DNAT'",
            "uci set firewall.sirene_dnat.dest='lan'",
            "# Service-IP muss auf dem RUT lokal ankommen -> auf WG-Interface legen",
            f"uci add_list network.{('wg_'+anchors[0]['id'])}.addresses='{service_ip}/32'",
            ""]
    L+=["# --- Firewall WG<->LAN ---",
        "uci -q get firewall.wgzone >/dev/null || { uci set firewall.wgzone=zone; uci set firewall.wgzone.name='wg'; uci set firewall.wgzone.input='ACCEPT'; uci set firewall.wgzone.output='ACCEPT'; uci set firewall.wgzone.forward='REJECT'; }",
        "uci -q delete firewall.wgzone.network || true"]
    for a in anchors: L.append(f"uci add_list firewall.wgzone.network='wg_{a['id']}'")
    L+=["uci -q get firewall.wg2lan >/dev/null || { uci set firewall.wg2lan=forwarding; uci set firewall.wg2lan.src='wg'; uci set firewall.wg2lan.dest='lan'; }",
        "uci -q get firewall.lan2wg >/dev/null || { uci set firewall.lan2wg=forwarding; uci set firewall.lan2wg.src='lan'; uci set firewall.lan2wg.dest='wg'; }",
        "","uci commit","/etc/init.d/network reload","/etc/init.d/firewall reload",
        f"echo 'OK {s['name']} konfiguriert'"]
    return "\n".join(L)+"\n"

def hub_outputs(cfg,keys):
    for a in active_anchors(cfg):
        peers=[f"# === Peers Pfad {a['id'].upper()} -> an /etc/wireguard/wg-{a['id']}.conf anhaengen ==="]
        pmap=[f"# <pubkey> <lan_subnet> <iface>  (Pfad {a['id']})"]
        for s in cfg["sites"]:
            pub=keys[(s['name'],a['id'])][1]
            peers+=["",f"# {s['name']} - LAN {s['lan_subnet']}","[Peer]",
                    f"PublicKey = {pub}", f"AllowedIPs = {tunnel_ip(cfg,a,s)}/32, {s['lan_subnet']}"]
            pmap.append(f"{pub} {s['lan_subnet']} wg-{a['id']}")
        open(os.path.join(OUT,"hub",f"{a['id']}.peers.conf"),"w").write("\n".join(peers)+"\n")
        open(os.path.join(OUT,"hub",f"{a['id']}.peer-map"),"w").write("\n".join(pmap)+"\n")

def main():
    cfg=load()
    for d in ("devices","hub","keys"): os.makedirs(os.path.join(OUT,d),exist_ok=True)
    anchors=active_anchors(cfg)
    if not anchors: sys.exit("Kein aktiver Anker.")
    keys={}
    for s in cfg["sites"]:
        for a in anchors: keys[(s['name'],a['id'])]=wg_keypair(s['name'],a['id'])
    for s in cfg["sites"]:
        open(os.path.join(OUT,"devices",f"{s['name']}.uci.sh"),"w",newline="\n").write(device_uci(cfg,s,keys))
    hub_outputs(cfg,keys)
    rows=[]
    for s in cfg["sites"]:
        gw,_=lan_gw(s); row={"standort":s['name'],"profil":s['profile'],"lan_subnet":s['lan_subnet'],"router_gw":gw}
        for a in anchors:
            row[f"tunnel_{a['id']}"]=tunnel_ip(cfg,a,s); row[f"pubkey_{a['id']}"]=keys[(s['name'],a['id'])][1][:12]+"..."
        rows.append(row)
    import csv as _c
    with open(os.path.join(OUT,"uebersicht.csv"),"w",newline="") as f:
        w=_c.DictWriter(f,fieldnames=list(rows[0].keys()),delimiter=";"); w.writeheader(); w.writerows(rows)
    print(f"OK (Muster A). Aktive Anker: {[a['id'] for a in anchors]}")
    print(f"  {len(cfg['sites'])} UCI-Skripte -> out/devices/")
    print(f"  Hub-Peers + peer-map -> out/hub/")
    print(f"  Keys -> out/keys/ (Private Keys chmod 600 - sicher lagern!)")

if __name__=="__main__": main()
