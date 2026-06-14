#!/bin/sh
# === EIN Befehl - macht alles. Du fasst nichts an. ===
# Reihenfolge wichtig: Excel liefert Stammdaten, anker_keys hat das letzte
# Wort bei den Pubkeys (autoritativ), dann Configs, dann Excel-Anzeige.
set -e
cd "$(dirname "$0")"
echo "[1/4] Excel -> YAML (Standorte, Index/Subnetz/Validierung automatisch)..."
python3 excel_to_yaml.py
echo "[2/4] Anker-Schluessel (Privkey zentral, Pubkey autoritativ in YAML)..."
python3 anker_keys.py
python3 resolve_endpoints.py --check 2>/dev/null || true
echo "[3/4] Geraete- & Hub-Configs erzeugen..."
python3 generate.py
echo "[4/4] Excel-Anzeige aus YAML zurueckschreiben..."
python3 yaml_to_excel.py
echo ""
echo "FERTIG. Du hast nichts von Hand gepflegt ausser Standort-Stammdaten."
echo "Naechster Schritt: out/ ausrollen (RMS + Anker-VM)."
