# RMS-Workflow: Router automatisch holen und konfigurieren

Das Tool laeuft auf dem Anker. Ablauf komplett ueber die Weboberflaeche:

## 1. Token hinterlegen (einmalig)
- In RMS: 2FA aktivieren, Personal Access Token erstellen.
- In der Weboberflaeche: Token ins Feld, "Token speichern".
- Der Token wird mit dem Master-Passwort (FELDNETZ_MASTER) VERSCHLUESSELT
  auf dem Anker abgelegt (secrets/rms_token.enc). Nie im Klartext.

## 2. Router aus RMS lesen ("Router aus RMS lesen")
Liest GET /devices: zeigt ID, Name, Modell, Serie (RUT2xx/RUTXxx/RUT9xx),
Status, Serial. So siehst du die ganze Flotte.

## 3. Zuordnen Sirene/Fahrzeug
In der Standort-Tabelle den Router als Zeile anlegen (Name = RMS-Geraetename!),
Typ waehlen:
  - sirene  -> internes LAN 192.168.1.0/24 BLEIBT, 1:1-NAT Service-IP -> .12
  - fahrzeug-> eigenes /27 geroutet
Index/Subnetz leer lassen -> automatisch vergeben.

## 4. Konfiguration erzeugen ("Konfiguration erzeugen")
Erzeugt Keys, UCI-Skripte (mit Sirenen-NAT bzw. Fahrzeug-Routing),
Anker-Peers.

## 5. Push
- "Push (Probelauf)": zeigt, welches Skript an welches Geraet ginge. Sendet nichts.
- "Push (scharf)": POST /devices/{id}/command je ONLINE-Geraet -> LAN/WLAN/VPN
  landen auf dem Router.

## Sirenen-NAT (wichtig)
Die Sirenensteuerung (192.168.1.12) bleibt unangetastet - du laeufst zu KEINER
Sirene. Du erreichst sie zentral ueber die eindeutige Service-IP
(z.B. sirene01 -> 192.168.80.2), der RUT uebersetzt das auf 192.168.1.12.

## Neue Teltonika spaeter integrieren
Router in RMS aufnehmen -> in der Tabelle als Zeile anlegen (Name=RMS-Name),
Typ waehlen -> erzeugen -> Push. Modell/Serie erkennt das Tool automatisch.

## Sicherheit
- Token verschluesselt (AES via Master-Passwort), nie im Repo.
- FELDNETZ_MASTER nur als ENV beim Start, nicht gespeichert.
- Tool nur intern/VPN. Push immer erst Probelauf.
