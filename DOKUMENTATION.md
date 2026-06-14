# Feldnetz Feuerwehr Musterstadt — Betriebsdokumentation

WireGuard-Feldnetz fuer 12 Sirenen + 5 Fahrzeuge (Teltonika RUT241, LTE/M2M)
ueber ein Hub-and-Spoke-VPN mit automatischem Rollout via RMS-API.

## 1. Architektur

    Router (RUT241, CGNAT)  --WireGuard UDP 51821-->  Sophos (198.51.100.10)
        |                                                   | DNAT
        | Endpoint: anker-a.vpn.example.org                   v
        |                                          Anker A (172.20.10.20, VLAN 900)
        |                                                   | BGP AS65101
        v                                                   v
    Sirenensteuerung 192.168.1.12  <--1:1-NAT--  px003 (AS65003) --> restl. Netz

- Supernetz:        192.168.80.0/20
- Sirenen:          192.168.80.0/24  (je /28 pro Standort)
- Fahrzeuge:        192.168.81.0/24  (je /27 pro Standort)
- Tunnel-Transfer:  10.80.1.0/24     (Hub = .254)
- Anker-Pubkey:     __HUB_A1_PUBLIC_KEY__
- WireGuard-IF:     wg-a1, ListenPort 51821

### Sirenen-NAT (1:1)
Jede Sirene hat intern fest 192.168.1.12 (Steuerung, wird NIE angefasst).
Pro Standort gibt es eine Service-IP = Netznummer + 2:
  - sirene01 (192.168.80.0/28)  -> Service-IP 192.168.80.2
  - Standort-02  (192.168.80.16/28) -> Service-IP 192.168.80.18
Die DNAT-Regel SIRENE-SVC auf dem Router uebersetzt Service-IP -> 192.168.1.12.

### Failover (Vodafone <-> Starlink)
Die SOPHOS macht das WAN-Failover. Die Router kennen nur EINEN Endpoint-Namen
(anker-a.vpn.example.org). Das DDNS-Skript haelt diesen Namen auf der jeweils
aktiven WAN-IP. Bei Failover folgt der DNS-Eintrag automatisch.

## 2. Komponenten (/opt/feldnetz)

- standorte.yaml / .xlsx     Quelle: alle Standorte, Anker, Subnetze
- generate.py                erzeugt UCI-Skripte + Hub-Peers + Keys
- push_rms.py                Rollout ueber RMS-API (Discover, Push, Diag)
- sync_anker.sh              laedt Hub-Peers in die laufende wg-a1.conf
- webapp/                    Weboberflaeche (Browser-Bedienung, Auto-Sync)
- keystore.py                verschluesselte Ablage des RMS-Tokens
- resolve_endpoints.py       Endpoint-Aufloesung pruefen
- ddns/netcup_ddns.py        DynDNS-Updater (Failover)
- wg-status.sh               wg show mit lesbaren Standortnamen

## 3. Rollout eines neuen Routers (Standardablauf)

1. Router auspacken, SIM + Strom -> geht in RMS auf "online"
2. Weboberflaeche http://172.20.10.20:8080 oeffnen, einloggen
3. "Router aus RMS holen" -> Router anhaken (Sirene/Fahrzeug) -> "uebernehmen"
4. "Konfiguration erzeugen"
5. "Push (scharf)"  -> Config geht per API auf den Router
                       danach laeuft sync_anker.sh AUTOMATISCH (Auto-Sync)
6. Tunnel pruefen:   /opt/feldnetz/wg-status.sh a1

Kommandozeile statt Weboberflaeche:
  cd /opt/feldnetz && . .venv/bin/activate
  export FELDNETZ_MASTER='<master-pw>'
  python3 generate.py
  python3 push_rms.py --only <NAME> --apply
  sudo ./sync_anker.sh a1

## 4. Test- und Pruefbefehle

### Tunnelstatus (mit Klarnamen)
  /opt/feldnetz/wg-status.sh a1

### Tunnelstatus (roh)
  sudo wg show wg-a1
  -> pro Peer "latest handshake" = Tunnel lebt; fehlt -> klopft nicht an

### Watchdog-Routen (werden bei frischem Handshake gesetzt)
  ip route | grep 192.168.8
  -> erwartet: 192.168.80.x/28 dev wg-a1

### BGP-Annonce zu px003
  sudo vtysh -c 'show ip bgp neighbors 172.20.10.10 advertised-routes' | grep 192.168.8

### Endpoint-DNS oeffentlich pruefen (NICHT lokal auf der VM!)
  nslookup anker-a.vpn.example.org 8.8.8.8
  -> muss 198.51.100.10 liefern
  ACHTUNG: ohne "8.8.8.8" fragt die VM ihren internen Resolver (falsche IP).

### Sirene erreichen (erst wenn Steuerung haengt)
  ping <Service-IP>      z.B. ping 192.168.80.18  (-> intern 192.168.1.12)

### DDNS manuell testen
  python3 /opt/feldnetz/ddns/netcup_ddns.py
  -> "Keine Aenderung: anker-a.vpn.example.org = <IP>" = ok

### DDNS-Cron laeuft?
  journalctl -u cron --since "15 min ago" | grep netcup

## 5. Fehlerbehebung (aus echten Faellen)

### Kein Handshake bei einem Router
Pruefe in dieser Reihenfolge (in der RMS-WebUI des Routers):

1. WIREGUARD ENABLED?  Services > VPN > WireGuard: Schalter "Enable" muss ON.
   Im Skript erzwungen durch: uci set network.wg_a1.disabled='0'
2. NAT-REGEL korrekt?  Network > Firewall: Regel SIRENE-SVC muss
   src_dip=<Service-IP> -> dest_ip=192.168.1.12 zeigen.
   (Haeufigste Ursache! Ein Fehler hier verhindert den Tunnel.)
3. PERSISTENT KEEPALIVE = 25?  Peer > Advanced settings. Ohne keepalive
   kommt der Router hinter CGNAT nicht durch.
4. ENDPOINT/DNS?  Peer > General: Endpoint anker-a.vpn.example.org.
   In der Router-Diagnostics nslookup testen. HINWEIS: "*** No answer"
   bezieht sich nur auf die IPv6-Abfrage (AAAA) und ist HARMLOS, solange
   "Address 1: 198.51.100.10" erscheint.
5. Pubkey-Abgleich:  der Anker-Pubkey im Peer muss
   __HUB_A1_PUBLIC_KEY__ sein.

### Peer fehlt auf dem Anker (kein latest handshake, kein Peer-Eintrag)
  sudo /opt/feldnetz/sync_anker.sh a1
  (laeuft beim Push automatisch; manuell nur bei Bedarf)

### DNS auf der VM zeigt falsche IP (192.168.5.11 statt .10)
Die VM nutzt einen internen Resolver. IRRELEVANT, weil die Router
oeffentliches DNS ueber Mobilfunk nutzen. Immer mit 8.8.8.8 testen.

### Ping auf 198.51.100.10 schlaegt fehl
Normal: die Sophos blockt eingehendes ICMP am WAN. WireGuard nutzt UDP
51821, nicht Ping. Kein Fehler.

### Sophos-NAT greift beim Failover nicht
Die DNAT-Regel DNAT-WG-A1 muss "Originales Ziel = Beliebig" haben und
BEIDE WAN-Schnittstellen (StarLink + WAN_P2) als eingehende Schnittstelle.
Sonst kommt der Verkehr ueber Starlink nicht an.

## 6. Sicherheit

- Private Geraete-Keys: out/keys/*.priv  (chmod 600, NIE weitergeben)
- RMS-Token:           verschluesselt via keystore (FELDNETZ_MASTER)
- DDNS-Geheimnisse:    ddns/netcup.conf  (chmod 600, in .gitignore)
- netcup-API-Key kann die GESAMTE DNS-Zone aendern -> wie Passwort behandeln.
  Bei Verdacht: im CCP neuen Key erzeugen, alten loeschen.
- NICHTS aus secrets/, out/keys/, out/devices/, out/hub/ gehoert ins Git.

## 7. Anker-VM Eckdaten
- Host:        anker-a-mitte, 172.20.10.20/24, VLAN 900, GW 172.20.10.1
- Dienste:     wg-a1 (WireGuard), frr (BGP), feldnetz-web (systemd), cron (DDNS)
- BGP:         AS65101, Peer px003 172.20.10.10 (AS65003)
- Watchdog:    annonciert /28 erst bei frischem Handshake
