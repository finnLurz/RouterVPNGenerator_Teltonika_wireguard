# Weiterentwicklung

Leitfaden für alle, die dieses Projekt übernehmen oder daran weiterarbeiten.

## Erst lesen

1. [README.md](README.md) – was das System macht.
2. [docs/ARCHITEKTUR.md](docs/ARCHITEKTUR.md) – wie es aufgebaut ist.
3. [docs/ENTSCHEIDUNGEN.md](docs/ENTSCHEIDUNGEN.md) – **warum** es so ist. Bevor du
   etwas grundlegend änderst, verstehe die hier dokumentierten Entscheidungen.

## Arbeitsumgebung

Der produktive Generator liegt auf der Anker-VM unter `/opt/feldnetz`. Änderungen
am Code sollten **erst** lokal/im Repo erfolgen, getestet, dann auf die VM
gebracht werden – nicht direkt auf der Produktiv-VM patchen (das wurde in der
Vergangenheit gemacht und führte fast zu verlorenen Fixes).

## Wichtige Werkzeuge

| Datei | Zweck |
|-------|-------|
| `generate.py` | erzeugt UCI-Skripte, Hub-Peers, Schlüssel aus `standorte.yaml` |
| `push_rms.py` | Rollout über RMS-API (`--discover`, `--apply`, `--diag`) |
| `sync_anker.sh` | lädt Hub-Peers in die laufende WireGuard-Konfiguration |
| `webapp/` | Weboberfläche (Flask) |
| `ddns/netcup_ddns.py` | DDNS-Updater für Failover |
| `zabbix/wg_monitor.py` | liefert Tunnel-Status an Zabbix |
| `wg-status.sh` | `wg show` mit lesbaren Standortnamen |

## Konventionen

- **Sprache:** Code-Kommentare und Doku auf Deutsch.
- **Schlüssel niemals committen.** Vor jedem Commit prüfen:
  ```bash
  git ls-files | grep -E '\.priv|\.privkey|\.uci\.sh|netcup\.conf|rms_token|\.salt'
  ```
  Muss leer sein.
- **Idempotenz:** UCI-Skripte und `sync_anker.sh` müssen mehrfach ausführbar sein,
  ohne Schaden anzurichten.
- **Service-IP = Netznummer + 2.** Diese Konvention nicht brechen.

## Typische Erweiterungen

- **Neuer Anker (a2/b1):** in `standorte.yaml` aktivieren, DNS/IP + Hub-Pubkeys
  eintragen, `generate.py` erzeugt dann mehrere Pfade pro Router.
- **Neues Gerätemodell:** Vorlage unter `models/` ergänzen.
- **Monitoring erweitern:** Templates und Items in Zabbix, siehe
  [docs/MONITORING.md](docs/MONITORING.md).

## Testen vor dem Ausrollen

- `generate.py` erzeugt Skripte → in `out/devices/` prüfen.
- Push immer erst als Probelauf (`push_rms.py` ohne `--apply`), dann scharf.
- Nach dem Push Tunnel mit `wg-status.sh a1` kontrollieren.

## Bei Fragen

Die meisten Stolpersteine sind in [docs/FEHLERBEHEBUNG.md](docs/FEHLERBEHEBUNG.md)
dokumentiert – inklusive der Fälle, die beim Erstaufbau tatsächlich aufgetreten
sind.

## Lizenz für Beiträge

Mit dem Einreichen eines Beitrags stimmst du zu, dass er unter derselben
Doppellizenz wie das Projekt bereitgestellt wird:
**Apache-2.0 OR GPL-3.0-only** (siehe [README.md](README.md#lizenz)). Bitte keine
echten Schlüssel, IP-Adressen, Domains oder Standortdaten in Beispielen oder
Commits – nur Platzhalter (`example.org`, `198.51.100.x`, `__…__`).
