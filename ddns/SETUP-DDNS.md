# netcup-DynDNS fuer den Anker-Endpunkt

Haelt anker-a.vpn.example.org automatisch auf der aktiven WAN-IP der Sophos.
Failover-sicher: bei Umschaltung Vodafone -> Starlink folgt der DNS-Eintrag.
DSGVO-konform, self-hosted, laeuft auf dem Anker.

## 1. netcup-API aktivieren (einmalig)
netcup CCP -> Stammdaten -> API:
  - API-Key erzeugen
  - API-Passwort erzeugen (SEPARAT vom CCP-Login!)
  - Kundennummer notieren

## 2. Config anlegen (Geheimnisse, NICHT ins Git)
  cd /opt/feldnetz/ddns
  cp netcup.conf.example netcup.conf
  nano netcup.conf        # apikey, apipassword, customernumber eintragen
  chmod 600 netcup.conf   # nur root/owner darf lesen

host = "anker-a.vpn"  (ohne Domain), domain = "example.org"
-> aktualisiert anker-a.vpn.example.org

## 3. Testlauf
  python3 netcup_ddns.py
  # Ausgabe: "anker-a.vpn.example.org: aktualisiert ... -> <eure IP>"
  # oder "Keine Aenderung" wenn schon korrekt

## 4. Als Cronjob (alle 2 Minuten)
  crontab -e
  */2 * * * * /usr/bin/python3 /opt/feldnetz/ddns/netcup_ddns.py --quiet >> /var/log/netcup-ddns.log 2>&1

## Wie es funktioniert
1. Ermittelt die aktuelle oeffentliche IPv4 (von aussen -> sieht die AKTIVE Leitung)
2. Holt die DNS-Records von netcup, findet anker-a.vpn (Typ A)
3. Weicht die IP ab -> aktualisiert NUR diesen Record (andere bleiben unberuehrt)
4. Logout

## Sicherheit
- netcup.conf: chmod 600, niemals ins Git (steht in .gitignore)
- API-Key kann eure ganze DNS-Zone aendern -> wie ein Passwort behandeln
- Bei Verdacht auf Kompromittierung: im CCP neuen API-Key erzeugen, alten loeschen
