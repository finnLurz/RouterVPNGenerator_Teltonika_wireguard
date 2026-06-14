# Router-Daten pflegen - du fasst nur die Excel an

> **Vorlage:** Diese öffentliche Vorlage enthält **keine** `standorte.xlsx`
> (die Originaldatei enthielt echte Standortdaten). Maßgebliche Quelle ist die
> beigelegte `standorte.yaml` mit Beispiel-Standorten – die kannst du direkt
> bearbeiten. Wer lieber mit Excel arbeitet, legt sich mit den Blättern
> `Standorte`, `Anker`, `Zentrale_Netze` eine eigene `standorte.xlsx` an
> (Spalten siehe unten) und nutzt dann `./build.sh`.

## Der EINE Befehl
    ./build.sh
Macht alles: Excel->YAML, Anker-Schluessel, Geraete-/Hub-Configs, Excel-Anzeige.

## Was DU pflegst (nur das)
In standorte.xlsx, Blatt "Standorte": eine Zeile pro RUT.
PFLICHT: name, profile (sirene|fahrzeug).
OPTIONAL (wird sonst automatisch vergeben): site_index, lan_subnet.
-> Laesst du Index/Subnetz leer, nummeriert das Tool sie selbst durch.

## Was AUTOMATISCH passiert (nie anfassen)
- alle WireGuard-Schluessel (Geraete + Anker), Pubkeys berechnet
- site_index + lan_subnet (wenn leer)
- Tunnel-IPs, Firewall, Routen, Peer-Listen, Watchdog-Map
- Validierung (Doppel-IP/Index, Subnetz-Ueberlappung) VOR dem Ausrollen

## Nur 3 echte Stammdaten (einmalig, Blatt "Anker")
- a1 endpoint_host: 198.51.100.10 (steht schon)
- a2 endpoint_host: DDNS-Name der Starlink-Leitung (wenn vorhanden)
- b1 endpoint_host: statische DSL-IP der Wache 2 (wenn vorhanden)
Die hub_public_key-Spalte NICHT ausfuellen - kommt automatisch.
