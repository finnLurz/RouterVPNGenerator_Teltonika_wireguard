# RMS-Push & Endpunkte - Bedienung

## Voraussetzung (einmalig)
1. RMS-Account: Zwei-Faktor-Authentifizierung aktivieren (Pflicht fuer API-Token).
2. Personal Access Token in RMS erstellen.
3. Token NUR als Umgebungsvariable setzen (nie ins Repo):
       export RMS_API_TOKEN='dein_token'

## Configs auf die Router pushen
    ./build.sh                       # Configs erzeugen
    python3 push_rms.py              # DRY-RUN: zeigt Zuordnung, sendet nichts
    python3 push_rms.py --apply      # scharf: CLI-Task je Geraet
    python3 push_rms.py --only sirene01 --apply   # nur ein Geraet

Der Dry-Run zeigt pro Standort: RMS-Geraete-ID, erkannte Serie (RUT2xx/
RUTXxx/RUT9xx), Modell und das Skript. Offline-Geraete und nicht in RMS
gefundene Standorte werden uebersprungen und gelistet.

WICHTIG: Standortname muss = RMS-Geraetename sein (Matching laeuft ueber den
Namen). In RMS die Geraete entsprechend benennen (sirene01, fzg01, ...).

## Multi-Modell (RUT241 / RUTX / RUT9xx)
- Die Serie wird automatisch aus RMS erkannt - kein manuelles Zuordnen.
- Da CLI-Tasks (Shell) genutzt werden, funktioniert der Push ueber alle drei
  Familien hinweg (anders als RMS-Config-Templates, die serien-gebunden sind).
- Modell-Eigenheiten stehen in models/*.yaml (z.B. WLAN aus bei RUTX/RUT9).

## Anker-Endpunkte: IP oder DNS-Name
In der Excel/YAML beim Anker entweder feste IP ODER DNS-Name eintragen.
Optionales Feld endpoint_mode:
  - 'ip'   : Name wird beim Generieren zu IP aufgeloest (python3 resolve_endpoints.py --write)
  - 'name' : Name bleibt - die RUTs loesen selbst auf (wie Netmaker).
             Dann genuegt spaeter EIN Eintrag im nginx/DNS, ohne Neugenerierung.

Pruefen, ob DNS-Namen aktuell aufloesen:
    python3 resolve_endpoints.py --check

## Sicherheit
- Token = maechtigstes Geheimnis (kann Geraete umkonfigurieren). Nie committen.
  Verschluesselt ablegen (SOPS) oder nur zur Laufzeit als ENV setzen.
- Immer erst --dry-run, dann --apply.
