# Installation

Aufsetzen des Feldnetzes von Grund auf – für den Fall, dass der Anker neu
aufgebaut werden muss.

> Alle Namen, IP-Adressen, VLANs und AS-Nummern in dieser Anleitung sind
> **Beispielwerte**. Ersetze sie durch die Werte deiner eigenen Umgebung.

## 1. Anker-VM bereitstellen

- Eine Linux-VM (hier: Debian) auf einem beliebigen Virtualisierungs-Host –
  **Proxmox, VMware vSphere/ESXi, Microsoft Hyper-V, KVM/libvirt o. Ä.** Das
  System stellt keine Anforderungen an die konkrete Virtualisierungslösung.
- **Wichtig – Netzanbindung:** Die VM muss in dem VLAN/Netz liegen, in dem auch
  Firewall/Gateway erreichbar sind. Stelle sicher, dass der Host dieses VLAN bis
  zur VM **durchreicht** (getaggter/Trunk-Port bzw. der passende virtuelle
  Switch/Portgruppe). Das ist je nach Host unterschiedlich konfiguriert – vorab
  prüfen, sonst ist die VM nicht erreichbar.
- Beispiel-Adressierung: IP `172.20.10.20/24`, Gateway `172.20.10.1`
  (Firewall/Gateway), im Server-VLAN (im Beispiel VLAN 900).
- Pakete: `wireguard-tools`, `frr`, `python3`, `python3-venv`, `cron`.
- IP-Forwarding aktivieren: `net.ipv4.ip_forward=1` in `/etc/sysctl.conf`.

## 2. Generator einspielen

```bash
sudo mkdir -p /opt/feldnetz
# Repository nach /opt/feldnetz klonen oder entpacken
cd /opt/feldnetz
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt   # falls vorhanden
```

## 3. WireGuard-Anker einrichten

- Interface `wg-a1`: Adresse `10.80.1.254/24`, ListenPort `51821`.
- Anker-Schlüsselpaar erzeugen (`anker_keys.py`), Pubkey notieren.
- Watchdog (systemd-Timer) einrichten, der bei frischem Handshake das jeweilige
  `/28` als Route setzt.

## 4. BGP (FRR)

- Lokales AS (Beispiel `AS65101`), Peer ist dein routender Nachbar (Router oder
  Firewall mit BGP; im Beispiel `172.20.10.10`, `AS65003`).
- FRR annonciert die vom Watchdog gesetzten Routen.

> BGP ist optional. Wer kein BGP fährt, kann die vom Watchdog gesetzten Routen
> auch statisch bzw. per Redistribution in sein Routing einbinden.

## 5. Eingehendes NAT auf der Firewall

Gilt für jede Firewall (z. B. Sophos, OPNsense/pfSense, Fortigate …) – die
Begriffe heißen je nach Hersteller anders, das Prinzip ist identisch:

- Dienst `WG-A1` = UDP `51821`.
- Host-Objekt `Anker-A` = `172.20.10.20`.
- **DNAT/Port-Forward** `DNAT-WG-A1`: Ziel = beliebig (bzw. die öffentliche IP),
  Dienst = `WG-A1`, übersetztes Ziel = `Anker-A`. Auf **allen** WAN-Schnittstellen
  aktivieren, über die der Tunnel ankommen soll (z. B. primäres WAN + Backup-/
  Starlink-Leitung).
- Passende Firewallregel: WAN → Zone/Netz des Ankers, Dienst `WG-A1`, Aktion
  „Zulassen".

## 6. DNS und DDNS

- DNS-Record `anker-a.vpn` (A) beim DNS-Anbieter, Startwert `198.51.100.10`,
  TTL `300`.
- `ddns/netcup.conf` aus `netcup.conf.example` anlegen (`chmod 600`),
  API-Zugangsdaten eintragen. (Beispiel nutzt netcup – für andere Anbieter das
  DDNS-Skript bzw. einen Standard-DDNS-Client entsprechend anpassen.)
- Cron: `*/2 * * * * /usr/bin/python3 /opt/feldnetz/ddns/netcup_ddns.py --quiet
  >> /var/log/netcup-ddns.log 2>&1`

## 7. Weboberfläche (optional, empfohlen)

- systemd-Dienst `feldnetz-web` (siehe `webapp/SETUP-WEBAPP.md`).
- Bindet auf `172.20.10.20:8080`.
- Umgebungsvariablen: `FELDNETZ_USER`, `FELDNETZ_PASS`, `FELDNETZ_MASTER`.
- Optional sudo-Regel für den Auto-Sync der Anker-Config (Details in
  `webapp/SETUP-WEBAPP.md`).

## 8. Monitoring

- Zabbix-Agent2 installieren, `wg_monitor.py` + UserParameter + sudo-Regel.
- `ServerActive=<zabbix-server>` (im Beispiel `192.168.5.81`),
  `Hostname=anker-a`.
- Details: [MONITORING.md](MONITORING.md).

## Reihenfolge der Inbetriebnahme

1. Anker-VM + WireGuard + BGP → Anker läuft.
2. Firewall-DNAT → Tunnel kommen durch.
3. DNS/DDNS → Endpunktname auflösbar und failover-fähig.
4. Ersten Test-Router pushen, Tunnel prüfen.
5. Monitoring aufsetzen.
6. Restliche Router ausrollen.
