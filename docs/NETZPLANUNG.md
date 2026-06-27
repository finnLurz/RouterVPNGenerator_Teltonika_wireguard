# Netzplanung – eigene IP-Bereiche, neue Netze, Subnetz-Assistent

Diese Anleitung zeigt, wie du den Generator auf **deine eigenen Adressbereiche**
einstellst, **weitere Netze** hinzufügst und dir die passende Subnetz-Größe
**automatisch vorschlagen** lässt. Nichts ist mehr fest verdrahtet – alles steckt
in `standorte.yaml` und lässt sich per Assistent pflegen.

---

## 1. Grundbegriffe

| Begriff | Bedeutung |
|---|---|
| **Pool** | Ein benannter Adressbereich (z. B. „Sirenen", „Fahrzeuge", „Messstellen"). Hat ein **Supernetz** und eine **Standort-Maske**. |
| **Supernetz** | Der große Bereich, aus dem die einzelnen Standorte geschnitten werden (z. B. `192.168.80.0/24`). |
| **Standort-Maske** (`host_prefix`) | Wie groß ein einzelner Router-Standort ist (z. B. `/28` = 14 nutzbare Adressen). |
| **Profil** | Das **Geräteverhalten** (z. B. `sirene` = internes LAN bleibt + Service-NAT, `fahrzeug` = geroutetes LAN). |
| **site_index** | Laufende Nummer je Standort (bestimmt die Tunnel-IP). Wird automatisch vergeben. |

Ein Pool verbindet **Adressierung** (Supernetz/Maske) mit einem **Profil**
(Verhalten). Standorte werden einem Pool zugeordnet – IP und Index kommen dann
automatisch.

---

## 2. Die wichtigsten Einstellungen (`standorte.yaml`)

Alle Stellschrauben an einem Ort. Auszug mit den relevanten Unterpunkten:

```yaml
global:
  tunnel_net_prefix: '10.80'      # Basis der WireGuard-Transfernetze (10.80.<pfad>.<index>)
  hub_host_octet: 254             # letzte Stelle der Hub-Tunnel-IP
  keepalive: 25                   # WireGuard PersistentKeepalive (Sekunden)
  routes_central:                 # zentrale Netze, die der Router durch den Tunnel erreicht
  - 192.168.0.0/20
  apn: wsim                       # Mobilfunk-APN der M2M-SIM

address_plan:
  pools:                          # << hier neue Netze hinzufügen
  - name: sirene                  # technischer Kurzname (= Zuordnung der Standorte)
    label: Sirenen                # Anzeigename
    profile: sirene               # Geräteverhalten (siehe 'profiles:')
    supernet: 192.168.80.0/24     # großer Bereich des Pools
    host_prefix: 28               # Größe je Standort (/28 = 14 nutzbar)
    index_start: 11               # erste site_index-Nummer dieses Pools
    advertise: true               # Supernetz ins Routing (BGP/OSPF) geben?

routing:
  protocol: bgp                   # bgp | ospf | both | none
  router_id: 172.20.10.20
  bgp:
    local_as: 65101
    neighbors:
    - { ip: 172.20.10.10, remote_as: 65003, description: Core-Router }
  ospf:
    area: 0.0.0.0
```

**Eigener IP-Bereich?** Es genügt, die `supernet`-Werte der Pools (und ggf.
`routes_central`, `tunnel_net_prefix`) auf deine Bereiche zu ändern – der Rest
rechnet sich daraus.

---

## 3. Welche Subnetz-Größe brauche ich? (Assistent)

Du musst Subnetze **nicht** selbst ausrechnen. Der Assistent fragt dich genau
**eine** der beiden Angaben ab und schlägt den Rest vor:

- **„Wie viele Endgeräte pro Router?"** → er wählt die kleinste passende
  Standort-Maske (inkl. Reserve fürs Gateway).
- **„Wie viele Router (Standorte)?"** → er wählt das passende Supernetz.

### Web (Klick-Anleitung)

1. Weboberfläche öffnen → oben rechts **„Netz-Assistent"** klicken.
2. Abschnitt **„1. Subnetz-Rechner"**:
   - „Größe bestimmen nach" auf **Endgeräte pro Router** stellen.
   - Zahl der Endgeräte eintragen (z. B. `12`) und Zahl der Router (z. B. `50`).
   - **Berechnen** → Vorschlag erscheint, z. B. *Standort-Maske /28, Supernetz /22*.
3. Die Felder unter **„2. Neues Netz"** werden automatisch vorbefüllt.

### Terminal

```bash
python3 wizard.py      # Menüpunkt [1] Subnetz-Rechner
```

### Referenz: Maske → nutzbare Adressen

| Maske | nutzbar je Standort | typisch für |
|------:|--------------------:|-------------|
| `/30` | 2  | 1 Gerät (z. B. nur Steuerung) |
| `/29` | 6  | bis 5 Geräte |
| `/28` | 14 | bis 13 Geräte (Standard Sirene) |
| `/27` | 30 | bis 29 Geräte (Standard Fahrzeug) |
| `/26` | 62 | bis 61 Geräte |
| `/24` | 254 | große Standorte |

---

## 4. Neues Netz (Pool) hinzufügen

### Variante A – Web (empfohlen, „Klick")

1. **Netz-Assistent** öffnen.
2. Erst **Subnetz-Rechner** ausfüllen und **Berechnen** (füllt Maske + Größe vor).
3. Abschnitt **„2. Neues Netz (Pool) anlegen"**:
   - **Kurzname** (technisch, z. B. `messstellen`)
   - **Anzeigename** (z. B. `Messstellen`)
   - **Geräteverhalten (Profil)** wählen (`sirene`/`fahrzeug`/…)
   - **Basis-Supernetz** eintragen (z. B. `192.168.96.0/23`)
   - **Standort-Maske** und **site_index Start** prüfen
   - **„ins Routing annoncieren"** an-/abhaken
4. **Pool anlegen** → wird sofort in `standorte.yaml` gespeichert und in der
   Pool-Tabelle angezeigt. Überlappungen mit vorhandenen Netzen werden abgelehnt.

### Variante B – Terminal

```bash
python3 wizard.py      # Menüpunkt [2] Neues Netz / Pool anlegen
```

### Variante C – direkt in der YAML

Einen Eintrag unter `address_plan.pools` ergänzen (Felder siehe Abschnitt 2).

---

## 5. Standort (Router) hinzufügen

- **Web:** Auf der Startseite Standort anlegen / aus RMS übernehmen – IP & Index
  werden automatisch aus dem Pool vergeben.
- **Terminal:** `python3 wizard.py` → **[3] Standort hinzufügen** → Pool wählen,
  Name eingeben. Fertig.

Bereits gesetzte Werte bleiben erhalten; nur leere Felder werden automatisch befüllt.

---

## 6. Routing (BGP / OSPF) einstellen

Im Block `routing:` das `protocol` setzen:

- `bgp` – nur BGP, `ospf` – nur OSPF, `both` – beides, `none` – kein dynamisches Routing.

Beim `python3 generate.py` (oder `python3 routing.py`) entsteht daraus
`out/anker/frr.conf`. Es werden **nur die lebenden** Standort-Routen verteilt
(der Watchdog setzt sie pro funktionierendem Tunnel) – gefiltert auf die
Pool-Supernetze mit `advertise: true`. So wird nie ein totes Netz annonciert.

> Pro Pool steuerst du mit `advertise: true|false`, ob sein Bereich ins Routing
> gegeben wird.

---

## 7. Weitergabe an Router & NetBox (Single Source of Truth)

`python3 generate.py` erzeugt zusätzlich:

- `out/devices/<name>.uci.sh` – fertige Router-Konfiguration (per RMS ausrollen).
- `out/ssot/netbox-import.json` – strukturierter Export (Pools, Prefixe je
  Standort, Tunnel, Routing) als **Andockpunkt für NetBox** o. ä.

Damit lassen sich die Daten automatisiert an die Geräte und an eine zentrale
Datenquelle weitergeben, statt sie doppelt zu pflegen.

---

## 8. Stabile Identität & Umbenennen (Seriennummer)

Jeder Standort ist über seine **`serial`** (Teltonika-Seriennummer) eindeutig
identifiziert – nicht über den Namen. Vorteil:

- Der **Name ist frei änderbar** (im Tool oder direkt in RMS), die Zuordnung und
  der WireGuard-Schlüssel bleiben gleich. Kein Tunnel-Bruch, kein Neu-Schlüsseln.
- Die **Schlüssel** liegen unter `out/keys/<serial>.<pfad>.{priv,pub}`.
- `push_rms.py` ordnet RMS-Geräte über die Serial zu (Name-Fallback, falls keine
  Serial gesetzt ist).
- Beim **„Router aus RMS holen"** wird die Serial automatisch mitgespeichert;
  bereits angelegte Router werden in der Liste ausgeblendet.

**Bestehende Installation umstellen** (einmalig, Schlüssel bleiben erhalten):
```bash
# Geräteliste (Name->Serial) aus RMS holen:
python3 push_rms.py --discover-json > devs.json     # mit gesetztem RMS-Token
# Migration: Probelauf, dann scharf (legt vorher ein Backup an):
python3 migrate_serial.py --from-json devs.json
python3 migrate_serial.py --from-json devs.json --apply
python3 generate.py                                 # out/devices muss identisch bleiben
```

## 9. Reihenfolge in Kürze

1. Eigene Bereiche in `standorte.yaml` setzen **oder** Pools per Assistent anlegen.
2. Standorte hinzufügen (Web / `wizard.py` / RMS-Import).
3. `python3 generate.py` → Geräte-Configs, `frr.conf`, NetBox-Export.
4. Ausrollen wie in [BETRIEB.md](BETRIEB.md) beschrieben.
