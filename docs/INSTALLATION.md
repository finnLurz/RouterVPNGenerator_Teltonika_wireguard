# Installation

Aufsetzen des Feldnetzes von Grund auf – für den Fall, dass der Anker neu
aufgebaut werden muss.

## 1. Anker-VM bereitstellen

- Debian-VM auf einem Proxmox-Host, der VLAN 900 durchreicht (px103, **nicht**
  px101 – px101 reicht VLAN 900 nicht durch).
- IP `172.20.10.20/24`, Gateway `172.20.10.1` (Sophos), VLAN 900.
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

- AS65101, Peer px003 (`172.20.10.10`, AS65003).
- FRR annonciert die vom Watchdog gesetzten Routen.

## 5. Sophos-DNAT

- Dienst `WG-A1` (UDP 51821).
- IP-Host `Anker-A` (172.20.10.20).
- NAT-Regel `DNAT-WG-A1`: Originales Ziel = Beliebig, Dienst = WG-A1,
  Übersetztes Ziel = Anker-A, eingehende Schnittstellen StarLink + WAN_P2.
- Firewallregel: WAN → Zone des Ankers, Dienst WG-A1, Aktion Zulassen.

## 6. DNS und DDNS

- DNS-Record `anker-a.vpn` (A) bei netcup, Startwert `198.51.100.10`, TTL 300.
- `ddns/netcup.conf` aus `netcup.conf.example` anlegen (chmod 600), netcup-API-
  Zugangsdaten eintragen.
- Cron: `*/2 * * * * /usr/bin/python3 /opt/feldnetz/ddns/netcup_ddns.py --quiet
  >> /var/log/netcup-ddns.log 2>&1`

## 7. Weboberfläche (optional, empfohlen)

- systemd-Dienst `feldnetz-web` (siehe `webapp/SETUP-WEBAPP.md`).
- Bindet auf `172.20.10.20:8080`.
- Umgebungsvariablen: `FELDNETZ_USER`, `FELDNETZ_PASS`, `FELDNETZ_MASTER`.
- sudo-Regel für Auto-Sync (`sync_anker.sh`) einrichten.

## 8. Monitoring

- Zabbix-Agent2 installieren, `wg_monitor.py` + UserParameter + sudo-Regel.
- `ServerActive=192.168.5.81`, `Hostname=anker-a-mitte`.
- Details: [MONITORING.md](MONITORING.md).

## Reihenfolge der Inbetriebnahme

1. Anker-VM + WireGuard + BGP → Anker läuft.
2. Sophos-DNAT → Tunnel kommen durch.
3. DNS/DDNS → Endpunktname auflösbar und failover-fähig.
4. Ersten Test-Router pushen, Tunnel prüfen.
5. Monitoring aufsetzen.
6. Restliche Router ausrollen.
