# Git-Repo einrichten (GitHub privat + SOPS/age)

WICHTIG: Repo MUSS **privat** sein. Enthaelt interne Netz-Topologie.
Die fertigen Configs (out/devices, out/hub, out/keys) werden per .gitignore
NICHT hochgeladen - sie entstehen lokal aus standorte.xlsx.

## 1. Werkzeuge installieren (einmalig, auf der Verwaltungs-Maschine)
    # Debian/Ubuntu:
    sudo apt install -y age
    # SOPS (von GitHub Releases, Beispiel):
    curl -LO https://github.com/getsops/sops/releases/latest/download/sops-v3.9.0.linux.amd64
    sudo install -m 0755 sops-v3.9.0.linux.amd64 /usr/local/bin/sops

## 2. age-Schluessel erzeugen (NIE committen!)
    mkdir -p ~/.config/sops/age
    age-keygen -o ~/.config/sops/age/keys.txt
    # Ausgabe: "Public key: age1xxxx..."  -> diesen in .sops.yaml eintragen
    grep -o 'age1[0-9a-z]*' ~/.config/sops/age/keys.txt   # Public key anzeigen

## 3. Private Keys verschluesselt ablegen
    python3 tools/collect_keys.py > /tmp/keys.yaml
    sops --encrypt /tmp/keys.yaml > secrets/keys.enc.yaml
    shred -u /tmp/keys.yaml      # Klartext-Zwischendatei sicher loeschen

## 4. Repo initialisieren und pushen
    git init
    git add .gitignore .sops.yaml *.py *.md standorte.xlsx standorte.yaml secrets/keys.enc.yaml tools/
    git commit -m "Feldnetz-Generator: Initial"
    git branch -M main
    git remote add origin git@github.com:<DEIN-USER>/feldnetz-oberursel.git
    git push -u origin main
    # (GitHub-Login/SSH-Key gibst DU ein - Repo vorher als PRIVATE anlegen!)

## 5. Auf neuem Rechner / Keys wiederherstellen
    git clone git@github.com:<DEIN-USER>/feldnetz-oberursel.git
    # age-keys.txt sicher mitbringen (NICHT aus dem Repo!)
    sops --decrypt secrets/keys.enc.yaml | python3 tools/restore_keys.py

## Was im Repo landet (und was NICHT)
  Im Repo:   standorte.xlsx, *.py, *.md, secrets/keys.enc.yaml (verschluesselt)
  NICHT:     out/keys/*.priv, out/devices/, out/hub/  (lokal generiert)
             ~/.config/sops/age/keys.txt  (dein privater age-Key)
