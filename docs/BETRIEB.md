# Betrieb

Tägliche Aufgaben rund um das Feldnetz. Der häufigste Fall ist das Ausrollen
eines neuen Routers.

## Neuen Router ausrollen

### Voraussetzung
- Router ist in RMS angelegt (per CSV-Import in der Company „Brand- und
  Zivilschutz Stadt Musterstadt").
- SIM eingelegt, Strom angeschlossen → Router zeigt in RMS „online".

### Über die Weboberfläche (empfohlen)

1. Browser öffnen: `http://172.20.10.20:8080`, anmelden.
2. **„Router aus RMS holen"** – die online-Router erscheinen.
3. Router **anhaken** und Typ wählen (Sirene oder Fahrzeug), **„übernehmen"**.
   Index und Subnetz werden automatisch vergeben.
4. **„Konfiguration erzeugen"** – erzeugt das UCI-Skript und die Anker-Peers.
5. **„Push (scharf)"** – die Konfiguration geht per RMS-API auf den Router.
   Danach läuft die Anker-Synchronisierung **automatisch** mit.
6. Tunnel prüfen: auf der Anker-VM `/opt/feldnetz/wg-status.sh a1` ausführen.

### Über die Kommandozeile (Alternative)

```bash
cd /opt/feldnetz
. .venv/bin/activate
export FELDNETZ_MASTER='<master-passwort>'

python3 generate.py                       # Konfiguration erzeugen
python3 push_rms.py --only <NAME> --apply # Push auf einen Router
sudo ./sync_anker.sh a1                   # Anker-Peers laden
```

## Tunnelstatus prüfen

```bash
# Mit lesbaren Standortnamen:
/opt/feldnetz/wg-status.sh a1

# Roh (Public Keys):
sudo wg show wg-a1
```

Pro Peer zeigt `latest handshake` an, dass der Tunnel lebt. Fehlt diese Zeile,
klopft der Router nicht an → siehe [FEHLERBEHEBUNG.md](FEHLERBEHEBUNG.md).

## Erreichbarkeit eines Standorts prüfen

```bash
# Watchdog-Route gesetzt?
ip route | grep 192.168.8

# BGP annonciert das Netz?
sudo vtysh -c 'show ip bgp neighbors 172.20.10.10 advertised-routes' | grep 192.168.8

# Sirene erreichbar (erst wenn Steuerung angeschlossen):
ping <Service-IP>      # z.B. 192.168.80.18
```

## Standort entfernen / deaktivieren

1. In `standorte.yaml` (oder Excel) den Standort entfernen bzw. auf inaktiv setzen.
2. `python3 generate.py` neu ausführen.
3. `sudo ./sync_anker.sh a1` – der Peer verschwindet aus der Anker-Konfiguration.

## DDNS prüfen (Failover-Funktion)

```bash
# Manueller Lauf:
python3 /opt/feldnetz/ddns/netcup_ddns.py
# Erwartung: "Keine Aenderung: anker-a.vpn.example.org = <IP>"

# Läuft der Cron?
journalctl -u cron --since "15 min ago" | grep netcup
```

## Wichtige Pfade

| Pfad | Inhalt |
|------|--------|
| `/opt/feldnetz/` | Generator, Werkzeuge, Weboberfläche |
| `/opt/feldnetz/standorte.yaml` | Quelle aller Standorte |
| `/opt/feldnetz/out/devices/` | erzeugte UCI-Skripte (enthalten Keys – nicht teilen) |
| `/opt/feldnetz/out/keys/` | private Schlüssel (chmod 600) |
| `/etc/wireguard/wg-a1.conf` | aktive Anker-Konfiguration |
| `/opt/feldnetz/ddns/netcup.conf` | DDNS-Zugangsdaten (chmod 600) |
