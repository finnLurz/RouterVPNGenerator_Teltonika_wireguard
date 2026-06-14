# Fehlerbehebung

Geordnet nach Symptom. Die meisten Fälle stammen aus dem realen Aufbau.

## Ein Router baut keinen Tunnel auf (kein Handshake)

Auf dem Anker zeigt `sudo wg show wg-a1` den Peer **ohne** `endpoint` und
`latest handshake`. Prüfe in dieser Reihenfolge in der RMS-WebUI des Routers:

### 1. Ist WireGuard aktiviert?
Services → VPN → WireGuard: Schalter **Enable** muss **on** sein.
Im Generator wird das erzwungen durch `uci set network.wg_a1.disabled='0'`.
Frisch ausgepackte Router haben das Interface sonst standardmäßig deaktiviert.

### 2. Stimmt die NAT-Regel? (häufigste Ursache!)
Network → Firewall: Die Regel `SIRENE-SVC` muss
`src_dip = <Service-IP>` → `dest_ip = 192.168.1.12` zeigen.
Ein Fehler hier verhindert den Tunnelaufbau komplett.

### 3. Persistent Keepalive gesetzt?
Peer → Advanced settings: **Persistent keep alive = 25**.
Ohne Keepalive kommt der Router hinter CGNAT nicht stabil durch.

### 4. Pubkey-Abgleich
Der Anker-Pubkey im Peer muss
`__HUB_A1_PUBLIC_KEY__` sein.

### 5. Erreicht das Paket den Anker überhaupt?
Wenn der Anker den Peer einträgt, aber **kein** Verbindungsversuch ankommt,
prüfe die Sophos-DNAT (UDP 51821 → 172.20.10.20) und dass die Firewallregel
aktiv ist.

## „No answer" bei nslookup auf dem Router

Beispiel:
```
Name:      anker-a.vpn.example.org
Address 1: 198.51.100.10
*** Can't find anker-a.vpn.example.org: No answer
```

**Das ist harmlos.** Das „No answer" bezieht sich nur auf die IPv6-Abfrage
(AAAA-Record), den es nicht gibt. Solange „Address 1: 198.51.100.10" erscheint,
funktioniert die IPv4-Auflösung. Kein Fehler.

## DNS auf der Anker-VM zeigt falsche IP

`nslookup anker-a.vpn.example.org` auf der VM liefert eine interne IP (z.B.
`192.168.5.11`) statt `198.51.100.10`.

**Ursache:** Die VM nutzt einen internen DNS-Resolver. Das ist **irrelevant**,
weil die Router öffentliches DNS über Mobilfunk nutzen. Zum Prüfen immer
öffentliches DNS erzwingen:
```bash
nslookup anker-a.vpn.example.org 8.8.8.8
```

## Ping auf 198.51.100.10 schlägt fehl

Normal. Die Sophos blockt eingehendes ICMP (Ping) auf dem WAN-Port. WireGuard
nutzt UDP 51821, nicht Ping. Der fehlgeschlagene Ping bedeutet **nicht**, dass
kein WireGuard durchkommt.

## Peer fehlt auf dem Anker

Der Router ist gepusht, aber `sudo wg show wg-a1` zeigt seinen Peer gar nicht.

```bash
sudo /opt/feldnetz/sync_anker.sh a1
```

Das lädt alle generierten Peers in die laufende Konfiguration (ohne Duplikate,
ohne bestehende Tunnel zu unterbrechen). Beim Push über die Weboberfläche läuft
dieser Schritt automatisch; manuell nur bei Bedarf.

## Failover greift nicht (Tunnel bricht bei Leitungswechsel)

Die Sophos-DNAT muss `Originales Ziel = Beliebig` haben und **beide** WAN-
Schnittstellen (StarLink + WAN_P2) als eingehende Schnittstelle. Sonst wird der
Verkehr, der nach dem Failover über Starlink kommt, nicht erkannt.

## RMS-Push meldet „OK", aber nichts passiert

Die RMS-Command-API arbeitet **asynchron**. „OK" / `"success": true` bedeutet
nur, dass der Befehl angenommen wurde – nicht, dass er schon ausgeführt ist.
Die tatsächliche Ausführung kann ein bis zwei Minuten dauern und erscheint im
RMS Task Manager.

## Zabbix: Item „Unknown metric"

`zabbix_agent2 -t 'wg.discover[a1]'` meldet `Unknown metric`.

- Stelle sicher, dass du auf der **Anker-VM** testest, nicht auf dem Zabbix-Server.
- Binary nicht im PATH? Voller Pfad: `sudo /usr/sbin/zabbix_agent2 -t '...'`
- Prüfe, dass `Include=/etc/zabbix/zabbix_agent2.d/*.conf` in
  `/etc/zabbix/zabbix_agent2.conf` gesetzt ist.

## Zabbix: Agent „active check configuration update failed"

Der Agent erreicht den Zabbix-Server nicht. Prüfe `ServerActive` in
`/etc/zabbix/zabbix_agent2.conf` – muss die **direkte IP** des Zabbix-Servers
sein (`192.168.5.81`), nicht der DNS-Name (der intern auf den Reverse-Proxy
zeigen kann). Test:
```bash
timeout 3 bash -c 'cat < /dev/null > /dev/tcp/192.168.5.81/10051' && echo erreichbar
```
