# Monitoring

Die Überwachung läuft über Zabbix (`zabbix.example.org`, Server `192.168.5.81`).

## WireGuard-Tunnelüberwachung

### Prinzip
Der Anker stellt über `wg show wg-a1` das Handshake-Alter aller Peers bereit.
Ein Skript (`zabbix/wg_monitor.py`) liefert diese Daten an den Zabbix-Agent.
Eine Low-Level-Discovery erkennt alle Peers automatisch; pro Peer wird das
Handshake-Alter überwacht und bei mehr als 5 Minuten ein Alarm ausgelöst.

### Bestandteile in Zabbix
- **Host:** `anker-a-mitte` (172.20.10.20)
- **Template:** `Feldnetz WireGuard by Agent`
  - LLD-Regel `wg.discover[a1]` – erkennt alle Peers (alle 5 Min)
  - Item-Prototyp `wg.peer.handshake.age[{#PUBKEY}]` – Handshake-Alter (alle 60s)
  - Trigger-Prototyp – Problem (Hoch), wenn Alter > 300 s
- Zusätzlich: Template `Linux by Zabbix agent` für CPU/RAM/Disk/Netzwerk der VM.

### Agent-seitige Einrichtung (Anker-VM)
- Skript: `/opt/feldnetz/zabbix/wg_monitor.py`
- UserParameter in `/etc/zabbix/zabbix_agent2.d/feldnetz-wg.conf`:
  ```
  UserParameter=wg.discover[*],sudo /opt/feldnetz/zabbix/wg_monitor.py discover $1
  UserParameter=wg.peer.handshake.age[*],sudo /opt/feldnetz/zabbix/wg_monitor.py age $1
  ```
- sudo-Regel (`/etc/sudoers.d/zabbix-wg`): der User `zabbix` darf **nur** dieses
  Skript als root ausführen (für `wg show`).
- `ServerActive=192.168.5.81` und `Hostname=anker-a-mitte` in
  `/etc/zabbix/zabbix_agent2.conf`.

### Lokal testen
```bash
sudo /usr/sbin/zabbix_agent2 -t 'wg.discover[a1]'
sudo /opt/feldnetz/zabbix/wg_monitor.py discover a1
sudo /opt/feldnetz/zabbix/wg_monitor.py age <pubkey> a1
```

### Was der Alarm bedeutet
„Feldnetz: <Standort> VPN-Handshake älter als 5 Minuten" → der Tunnel zu diesem
Standort ist vermutlich down. Mögliche Ursachen: SIM/Strom/Mobilfunk am Router,
Sophos-DNAT, oder der Router selbst. Siehe [FEHLERBEHEBUNG.md](FEHLERBEHEBUNG.md).

## Netzwerkgeräte (geplant / im Aufbau)

- **Teltonika-Router:** per SNMP (Signalstärke, Datenverbrauch, WAN-Status).
  SNMP wird im Generator aktiviert; Zabbix erreicht die Router über ihre
  Service-IPs durch den Tunnel. Hinweis: SNMP-Werte kommen nur, wenn der Tunnel
  steht – der Handshake-Alarm bleibt davon unabhängig.
- **Sophos, Switches:** per SNMP mit den jeweiligen Zabbix-Templates.
- **Proxmox-Cluster:** über die Proxmox-Templates.

## Visualisierung

Aktuell Zabbix-Dashboards. Für aufwendigere Visualisierung kann Grafana mit
Zabbix als Datenquelle angebunden werden (geplant).
