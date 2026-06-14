# Feldnetz Feuerwehr Musterstadt

Automatisiertes WireGuard-VPN für die Anbindung von Sirenen und Einsatzfahrzeugen
der Feuerwehr Musterstadt über Mobilfunk (Teltonika RUT241, LTE/M2M).

Das System rollt Router automatisch über die Teltonika-RMS-API aus, baut
verschlüsselte Tunnel zu einem zentralen Anker auf, hält die Erreichbarkeit
über DDNS-Failover stabil und überwacht alle Tunnel in Zabbix.

> **Hinweis – das ist eine Vorlage.** Dieses Repository ist eine generische,
> anonymisierte Vorlage zum Nachbauen. Alle Namen, Domains, IP-Adressen und
> Schlüssel (`example.org`, `198.51.100.x`, `Musterstadt`, `__…__`-Platzhalter)
> sind Beispielwerte und müssen durch deine eigenen ersetzt werden.
> **Deine produktive Installation** mit echter Netz-Topologie und echten
> Schlüsseln gehört in ein **privates** Repository – siehe
> [SETUP-GIT.md](SETUP-GIT.md).

---

## Was kann das System?

- **Automatischer Rollout**: Neue Router werden über eine Weboberfläche oder die
  Kommandozeile konfiguriert und per RMS-API ausgerollt – ohne Gerät einzeln anzufassen.
- **Hub-and-Spoke-VPN**: Alle Router verbinden sich verschlüsselt zu einem zentralen
  Anker; das interne Netz wird per BGP verteilt.
- **Failover**: Die Erreichbarkeit folgt automatisch der aktiven Internetleitung
  (Vodafone ↔ Starlink) über DDNS.
- **Sirenen-NAT**: Die Sirenensteuerung ist über eine feste Service-IP erreichbar,
  ohne die Steuerung selbst anzufassen.
- **Monitoring**: Zabbix überwacht jeden Tunnel und alarmiert, wenn ein Handshake
  länger als 5 Minuten ausbleibt.

---

## Schnelleinstieg (für Eilige)

Einen neuen Router in Betrieb nehmen:

1. Router auspacken, SIM einlegen, Strom anschließen → Router meldet sich in RMS.
2. Weboberfläche öffnen: `http://172.20.10.20:8080`
3. „Router aus RMS holen" → Router anhaken (Sirene/Fahrzeug) → „übernehmen"
4. „Konfiguration erzeugen" → „Push (scharf)"
5. Tunnel prüfen: `/opt/feldnetz/wg-status.sh a1`

Ausführlich: siehe [docs/BETRIEB.md](docs/BETRIEB.md).

---

## Dokumentation

| Datei | Inhalt |
|-------|--------|
| [docs/ARCHITEKTUR.md](docs/ARCHITEKTUR.md) | Aufbau, Netze, Komponenten, Datenfluss |
| [docs/INSTALLATION.md](docs/INSTALLATION.md) | Anker und Werkzeuge von Grund auf aufsetzen |
| [docs/BETRIEB.md](docs/BETRIEB.md) | Täglicher Betrieb: Router ausrollen, Schritt für Schritt |
| [docs/FEHLERBEHEBUNG.md](docs/FEHLERBEHEBUNG.md) | Häufige Probleme und ihre Lösung |
| [docs/MONITORING.md](docs/MONITORING.md) | Zabbix-Überwachung, Alarme, Templates |
| [docs/ENTSCHEIDUNGEN.md](docs/ENTSCHEIDUNGEN.md) | Warum das System so gebaut ist (für Weiterentwickler) |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Wie man hier weiterentwickelt |

### Generator & technische Referenz

Der Konfigurations-Generator (eine Quelle der Wahrheit `standorte.yaml` →
Geräte-/Hub-Configs) und seine Bedienung sind separat dokumentiert:

| Datei | Inhalt |
|-------|--------|
| [GENERATOR.md](GENERATOR.md) | Generator-Workflow, Artefakt-Typen, Design-Invarianten |
| [DOKUMENTATION.md](DOKUMENTATION.md) | Vollständige Betriebsdokumentation des Feldnetzes |
| [PFLEGE.md](PFLEGE.md) | Router-Daten über Excel pflegen (`build.sh`) |
| [RMS-WORKFLOW.md](RMS-WORKFLOW.md) | Router über die RMS-API holen und konfigurieren |
| [RMS-API.md](RMS-API.md) | RMS-Push & Endpunkte – Bedienung |
| [SETUP-GIT.md](SETUP-GIT.md) | Git-Repo (privat) mit SOPS/age einrichten |
| [webapp/SETUP-WEBAPP.md](webapp/SETUP-WEBAPP.md) | Weboberfläche aufsetzen |
| [ddns/SETUP-DDNS.md](ddns/SETUP-DDNS.md) | DDNS-Failover (netcup) einrichten |
| [models/README.md](models/README.md) | Geräte-Modelle (Teltonika) pflegen |

---

## Wichtigste Eckdaten

| | |
|---|---|
| Anker A | `172.20.10.20` (VLAN 900), WireGuard `wg-a1`, Port `51821` |
| Öffentlicher Endpunkt | `anker-a.vpn.example.org` → Sophos `198.51.100.10` |
| Supernetz | `192.168.80.0/20` (Sirenen /28, Fahrzeuge /27) |
| Tunnel-Transfernetz | `10.80.1.0/24` (Hub = `.254`) |
| Zabbix | `192.168.5.81`, Weboberfläche `zabbix.example.org` |

---

## Sicherheit

Dieses Repository enthält **keine** Geheimnisse. Private Schlüssel, API-Tokens und
Zugangsdaten liegen ausschließlich auf den Systemen und sind über `.gitignore`
ausgeschlossen. Siehe [docs/ENTSCHEIDUNGEN.md](docs/ENTSCHEIDUNGEN.md#sicherheit)
für Details zur Schlüsselverwaltung.

Die in dieser Vorlage enthaltenen WireGuard-Schlüssel sind Platzhalter
(`__HUB_A1_PUBLIC_KEY__` usw.). Erzeuge für deine Installation eigene Schlüssel –
private Schlüssel entstehen ausschließlich lokal auf den Geräten.

---

## Lizenz

Dieses Projekt ist **dual lizenziert**: Du kannst es **wahlweise** unter den
Bedingungen der [Apache License 2.0](LICENSE-APACHE) **ODER** der
[GNU General Public License v3.0](LICENSE-GPL) nutzen – such dir die Lizenz aus,
die zu deinem Vorhaben passt (*„Apache-2.0 OR GPL-3.0, at your option"*).

SPDX-Kennung: `Apache-2.0 OR GPL-3.0-only`

Sofern du einen Beitrag (Pull Request) einreichst, stimmst du zu, dass dein
Beitrag unter denselben beiden Lizenzen bereitgestellt wird.
