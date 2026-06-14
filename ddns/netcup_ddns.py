#!/usr/bin/env python3
"""
netcup_ddns.py - DSGVO-konformer DynDNS-Updater fuer netcup.

Haelt EINEN A-Record (z.B. anker-a.vpn.example.org) auf der aktuellen
oeffentlichen WAN-IP der Sophos. Failover-sicher: ermittelt die TATSAECHLICH
aktive IP (egal ob Vodafone oder Starlink), weil der Abruf von aussen kommt.

WICHTIG: updateDnsRecords der netcup-API kann die ganze Zone ueberschreiben.
Dieses Skript aendert NUR den einen Ziel-Record (per Record-ID), alle anderen
bleiben unangetastet.

Geheimnisse kommen aus ddns/netcup.conf (chmod 600), NICHT aus dem Code.
"""
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CONF = os.path.join(HERE, "netcup.conf")
API = "https://ccp.netcup.net/run/webservice/servers/endpoint.php?JSON"


def load_conf():
    if not os.path.exists(CONF):
        sys.exit(f"Config fehlt: {CONF} (aus netcup.conf.example erstellen, chmod 600)")
    with open(CONF) as f:
        c = json.load(f)
    for k in ("apikey", "apipassword", "customernumber", "domain", "host"):
        if not c.get(k):
            sys.exit(f"Config: '{k}' fehlt.")
    return c


def api_call(action, param):
    data = json.dumps({"action": action, "param": param}).encode()
    req = urllib.request.Request(API, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def get_public_ip():
    """Aktuelle oeffentliche IPv4 - sieht die AKTIVE Leitung (Failover-sicher)."""
    # mehrere Quellen, falls eine ausfaellt
    for url in ("https://api.ipify.org", "https://ipv4.icanhazip.com",
                "https://v4.ident.me"):
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                ip = r.read().decode().strip()
                if ip.count(".") == 3:
                    return ip
        except Exception:
            continue
    sys.exit("Konnte oeffentliche IP nicht ermitteln.")


def main():
    quiet = "--quiet" in sys.argv
    c = load_conf()

    # 1. Login
    login = api_call("login", {
        "apikey": c["apikey"], "apipassword": c["apipassword"],
        "customernumber": c["customernumber"]})
    if login.get("status") != "success":
        sys.exit(f"Login fehlgeschlagen: {login.get('longmessage')}")
    sid = login["responsedata"]["apisessionid"]

    try:
        # 2. Aktuelle Records holen
        info = api_call("infoDnsRecords", {
            "apikey": c["apikey"], "apisessionid": sid,
            "customernumber": c["customernumber"], "domainname": c["domain"]})
        if info.get("status") != "success":
            sys.exit(f"infoDnsRecords: {info.get('longmessage')}")
        records = info["responsedata"]["dnsrecords"]

        # Ziel-Record finden (host + type A)
        target = None
        for rec in records:
            if rec.get("hostname") == c["host"] and rec.get("type") == "A":
                target = rec
                break

        wan_ip = get_public_ip()

        if target and target.get("destination") == wan_ip:
            if not quiet:
                print(f"Keine Aenderung: {c['host']}.{c['domain']} = {wan_ip}")
            return

        # 3. Nur den EINEN Record aktualisieren (per ID, Rest unberuehrt)
        if target:
            target["destination"] = wan_ip
            rec_to_send = target
            action_txt = f"aktualisiert {target.get('destination')} -> {wan_ip}"
        else:
            # Record existiert noch nicht -> neu anlegen
            rec_to_send = {"hostname": c["host"], "type": "A",
                           "destination": wan_ip}
            action_txt = f"neu angelegt -> {wan_ip}"

        upd = api_call("updateDnsRecords", {
            "apikey": c["apikey"], "apisessionid": sid,
            "customernumber": c["customernumber"], "domainname": c["domain"],
            "dnsrecordset": {"dnsrecords": [rec_to_send]}})
        if upd.get("status") != "success":
            sys.exit(f"updateDnsRecords: {upd.get('longmessage')}")
        print(f"{c['host']}.{c['domain']}: {action_txt}")

    finally:
        # 4. Logout
        api_call("logout", {
            "apikey": c["apikey"], "apisessionid": sid,
            "customernumber": c["customernumber"]})


if __name__ == "__main__":
    main()
