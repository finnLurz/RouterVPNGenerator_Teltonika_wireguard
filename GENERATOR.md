# Feldnetz-Generator Feuerwehr Musterstadt

Eine Quelle der Wahrheit (`standorte.yaml`), drei Artefakt-Typen:

| Ausgabe | Zweck |
|---|---|
| `out/devices/<site>.setup.sh` | Komplettes RutOS-Setup je Geraet (WG-Pfade, Routen, Firewall, Gast, Watchdog). Push + Ausfuehrung via RMS Task Manager. Idempotent: mehrfach ausfuehrbar. |
| `out/hub/<anker>.{interface,peers}.conf` | WireGuard-Konfig je Concentrator-Interface (A: wg-DSL + wg-Starlink, B: wg-DSL) |
| `out/uebersicht.csv` | Doku/Excel-Import, zeigt fehlende Pubkeys |

## Workflow

1. `standorte.yaml` pflegen (Anker-Pubkeys, Wache-B-IP, DDNS-Name eintragen)
2. `python3 generate.py`
3. **Phase 1:** Setup-Skripte via RMS auf Geraete pushen + ausfuehren.
   Jedes Geraet generiert seine Keys LOKAL und gibt Pubkeys aus
   (RMS-Task-Output bzw. /tmp/wg-pubkeys.txt).
4. Pubkeys in `standorte.yaml` eintragen, erneut `generate.py`
5. **Phase 2:** `out/hub/*.peers.conf` auf Concentratoren einspielen
   (wg addconf bzw. an wgX.conf anhaengen, wg-quick restart).
   Setup-Skripte erneut pushen (no-op ausser Aenderungen).
6. Aenderung am Bestand? -> nur YAML aendern, ab Schritt 2 wiederholen.

## Design-Invarianten

- Private Keys verlassen NIE das Geraet (entstehen via `wg genkey` lokal)
- Ein Schluesselpaar PRO PFAD (a1/a2/b1) -> Hub-seitig keine
  AllowedIPs-Kollisionen, Pfade unabhaengig revozierbar
- `route_allowed_ips=0`: Routen verwaltet ausschliesslich der Watchdog
  (Metrik 10/20/30), kein automatisches Routen-Chaos
- Watchdog: Ping auf Hub-Transfer-IP je Pfad, 3 Fehlschlaege -> Routen
  des Pfads entfernt, Recovery automatisch beim naechsten erfolgreichen Ping
- Gastnetz (Fahrzeuge): eigene Zone, nur guest->wan, nie im Tunnel

## Offene Platzhalter (vor Phase 1 setzen)

- `__HUB_A_WG1_PUBKEY__`, `__HUB_A_WG2_PUBKEY__`, `__HUB_B_WG1_PUBKEY__`
- `__WACHE_B_IP__` (Kandidat: 198.51.100.20 = fwf002, zuordnen!)
- `hub-a2.example.ddns` (DDNS fuer Starlink-Public-IP an Mitte)
