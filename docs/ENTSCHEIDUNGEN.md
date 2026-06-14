# Entscheidungen

Dieses Dokument hält fest, **warum** das System so gebaut ist. Für
Weiterentwickler ist das oft wichtiger als der Code selbst, weil es erklärt,
welche Alternativen verworfen wurden und aus welchem Grund.

## Hub-and-Spoke statt Mesh

**Entscheidung:** Alle Router verbinden sich zu einem zentralen Anker, nicht
untereinander.

**Begründung:** Sirenen und Fahrzeuge müssen nur die zentrale Infrastruktur
erreichen, nicht sich gegenseitig. Ein Hub-and-Spoke ist einfacher zu
betreiben, zu überwachen und abzusichern. Eine einzige Sophos-DNAT-Regel
genügt für die ganze Flotte.

## Failover über DNS, nicht über mehrere Tunnel

**Entscheidung:** Jeder Router baut **einen** Tunnel zu einem DNS-Namen auf.
Das Failover macht die Sophos (WAN-Umschaltung), der DNS-Name folgt per DDNS.

**Verworfene Alternative:** Pro Router mehrere Tunnel zu mehreren Ankern
(Multi-Peer mit BGP-Failover).

**Begründung:** Die Sophos macht ohnehin schon WAN-Failover (Vodafone ↔
Starlink). Eine zweite Anker-VM, Multi-Peer-Konfiguration und BGP-Failover
hätten den Aufbau deutlich verkompliziert, ohne echten Mehrwert – das Failover
passiert unterhalb von WireGuard. Mit DNS+DDNS bleibt es bei einem Tunnel und
einer Anker-VM. Voraussetzung: Die Failover-Leitung (Starlink) braucht eine
öffentliche IP, damit die Router den Anker auch darüber erreichen.

## DDNS per eigenem Skript statt Sophos-DynDNS

**Entscheidung:** Ein eigenes Python-Skript (`ddns/netcup_ddns.py`) aktualisiert
den DNS-Eintrag bei netcup.

**Begründung:** netcup ist kein unterstützter DynDNS-Anbieter in der Sophos.
Das Skript ist self-hosted, DSGVO-konform und ändert gezielt **nur** den einen
Anker-Record (die übrige Zone bleibt unberührt). Es ermittelt die öffentliche
IP von außen und sieht damit immer die tatsächlich aktive Leitung.

## Sirenen-NAT (1:1) statt geroutetem Steuerungsnetz

**Entscheidung:** Die Sirenensteuerung behält intern fest `192.168.1.12`. Eine
DNAT-Regel auf dem Router übersetzt eine eindeutige Service-IP → `192.168.1.12`.

**Begründung:** Die Steuerungen sind vorkonfiguriert und sollen **nicht**
angefasst werden (Gewährleistung, einheitliche Wartung). Über die Service-IP
(Netznummer + 2) ist jede Sirene eindeutig adressierbar, obwohl sie intern alle
dieselbe IP haben.

## Konfiguration zentral erzeugt, per UCI-Set-Skript verteilt

**Entscheidung:** Schlüssel werden zentral erzeugt; der Generator schreibt
idempotente UCI-Set-Skripte, die per RMS-Command-API ausgeführt werden.

**Begründung:** Funktioniert über alle Teltonika-Serien hinweg, passt zu
individuellen Schlüsseln pro Gerät und ist wiederholbar (idempotent). Der
Push-Weg „CLI-Command" wurde gegenüber „Configuration-Template" gewählt, weil
er flexibler mit gerätespezifischen Werten umgeht.

## Monitoring vom Anker aus, nicht von den Routern

**Entscheidung:** Zabbix überwacht den Handshake-Status über den **Anker**
(`wg show wg-a1`), nicht durch direkte Abfrage jedes Routers.

**Begründung:** Würde man die Router durch den Tunnel überwachen, verlöre man
beim Tunnelausfall **gleichzeitig** Verbindung und Überwachung – man wüsste nie,
ob „Router weg" oder „nur Monitoring weg". Vom Anker aus ist der Handshake-Status
immer sichtbar, auch wenn der Tunnel tot ist. Die per-Router-Details (Signal,
Datenverbrauch) kommen ergänzend per SNMP durch den Tunnel.

## Sicherheit

### Schlüsselverwaltung
- Private WireGuard-Schlüssel liegen unter `out/keys/*.priv` (chmod 600) und
  stecken in den UCI-Skripten. Sie werden **nie** ins Git committet
  (`.gitignore`).
- Der RMS-API-Token liegt verschlüsselt (Fernet/AES, Master-Passwort aus
  `FELDNETZ_MASTER`), nicht im Klartext.
- DDNS-Zugangsdaten in `ddns/netcup.conf` (chmod 600, in `.gitignore`).

### Was nie ins Repository gehört
`secrets/`, `out/keys/`, `out/devices/`, `out/hub/`, `*.priv`, `*.privkey`,
`ddns/netcup.conf`, `*.salt`, `rms_token.enc`. Die `.gitignore` deckt das ab.

### Bei Verdacht auf Kompromittierung
- netcup-API-Key: im CCP neuen erzeugen, alten löschen.
- WireGuard-Keys: neu erzeugen (`generate.py`), Router neu pushen.
- Zabbix-Token: in den Benutzereinstellungen neu erzeugen.
