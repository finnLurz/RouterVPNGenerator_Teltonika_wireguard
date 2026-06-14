#!/bin/bash
# wg-status.sh - zeigt wg show mit lesbaren Standortnamen statt Public Keys.
# Baut die Zuordnung aus den out/hub/*.peers.conf (Kommentar + PublicKey).
ANKER="${1:-a1}"
PEERS="/opt/feldnetz/out/hub/${ANKER}.peers.conf"

# Zuordnung Pubkey -> Name aus der peers.conf lesen
declare -A NAMES
name=""
while IFS= read -r line; do
  # Kommentarzeile mit Standortname: "# Standort-02 - LAN ..."
  if [[ "$line" =~ ^#[[:space:]]*([^[:space:]]+)[[:space:]]*-[[:space:]]*LAN ]]; then
    name="${BASH_REMATCH[1]}"
  fi
  # PublicKey-Zeile
  if [[ "$line" =~ ^PublicKey[[:space:]]*=[[:space:]]*(.+)$ ]]; then
    key="${BASH_REMATCH[1]}"
    NAMES["$key"]="$name"
  fi
done < "$PEERS"

# wg show durchgehen und Keys ersetzen
sudo wg show "wg-${ANKER}" | while IFS= read -r line; do
  if [[ "$line" =~ ^peer:[[:space:]]*(.+)$ ]]; then
    key="${BASH_REMATCH[1]}"
    pubkey=$(echo "$key" | tr -d ' ')
    nm="${NAMES[$pubkey]}"
    if [[ -n "$nm" ]]; then
      echo "peer: $nm  [$pubkey]"
    else
      echo "$line  (unbekannt)"
    fi
  else
    echo "$line"
  fi
done
