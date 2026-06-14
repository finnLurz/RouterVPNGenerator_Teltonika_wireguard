# Feldnetz-Generator Web-Oberflaeche - Setup auf Ubuntu-VM

Bedienung im Browser, auch fuer Kollegen ohne Terminal.
WICHTIG (BOS): NUR intern/VPN betreiben. Niemals ins Internet exponieren.

## 1. VM vorbereiten
    sudo apt update && sudo apt install -y python3-pip python3-venv wireguard-tools git
    git clone <euer-repo> /opt/feldnetz   # oder Ordner hochladen
    cd /opt/feldnetz
    python3 -m venv .venv && . .venv/bin/activate
    pip install -r webapp/requirements.txt

## 2. Zugang festlegen (Login-Daten + sichere Bindung)
    # Passwort + an welche IP gebunden wird (VPN-/interne IP der VM):
    export FELDNETZ_USER=feuerwehr
    export FELDNETZ_PASS='EinStarkesPasswort!'      # PFLICHT
    export FELDNETZ_SECRET="$(python3 -c 'import secrets;print(secrets.token_hex(32))')"
    export FELDNETZ_MASTER="EinMasterPwFuerTokenVerschluesselung!"   # entsperrt RMS-Token
    export FELDNETZ_BIND=10.10.0.5     # interne/VPN-IP der VM (NICHT 0.0.0.0!)
    export FELDNETZ_PORT=8080

## 3. Starten (Test)
    . .venv/bin/activate
    python3 webapp/app.py
    # Browser: http://<interne-IP>:8080  -> Login -> Standorte -> "Konfiguration erzeugen" -> ZIP

## 4. Als Dienst (dauerhaft) - systemd
Datei /etc/systemd/system/feldnetz-web.service:
    [Unit]
    Description=Feldnetz-Generator Web
    After=network.target
    [Service]
    WorkingDirectory=/opt/feldnetz
    Environment=FELDNETZ_USER=feuerwehr
    Environment=FELDNETZ_PASS=EinStarkesPasswort!
    Environment=FELDNETZ_BIND=10.10.0.5
    Environment=FELDNETZ_PORT=8080
    ExecStart=/opt/feldnetz/.venv/bin/python3 webapp/app.py
    Restart=on-failure
    User=feldnetz
    [Install]
    WantedBy=multi-user.target

    sudo systemctl daemon-reload && sudo systemctl enable --now feldnetz-web

## 5. Absichern (Pflicht bei BOS)
- FELDNETZ_BIND = interne/VPN-IP, NIE 0.0.0.0 oder oeffentlich.
- Firewall: Port 8080 nur aus dem Verwaltungs-/VPN-Netz erlauben.
- Optional: hinter Nginx mit HTTPS (selbstsigniert/interne CA).
- Die erzeugten Keys liegen in out/ auf der VM - Zugriff auf die VM beschraenken.

## Was die Oberflaeche kann
- Standorte in Tabelle bearbeiten (Name + Typ; Index/Subnetz automatisch)
- "Konfiguration erzeugen" -> Schluessel, Geraete-/Hub-Configs
- ZIP herunterladen (fuer RMS-Rollout + Anker-VM)
Anker/DDNS/Wache-B-IP werden weiter ueber Excel/YAML gepflegt.
