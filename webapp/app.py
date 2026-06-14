#!/usr/bin/env python3
"""
Feldnetz-Generator - Web-Oberflaeche (Flask)
Self-hosted, NUR intern/VPN betreiben. Login-geschuetzt.
Bedienung ohne Terminal: Standorte bearbeiten -> Generieren -> ZIP laden.
"""
import os, sys, io, json, zipfile, subprocess, ipaddress, secrets, functools
from datetime import datetime
from flask import (Flask, render_template, request, redirect, url_for,
                   session, send_file, flash, jsonify)
import yaml, subprocess as _sp
sys_path = os.path.dirname(BASE) if False else None

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YAML = os.path.join(BASE, "standorte.yaml")
OUT = os.path.join(BASE, "out")
VALID_PROFILES = ["sirene", "fahrzeug"]

app = Flask(__name__)
app.secret_key = os.environ.get("FELDNETZ_SECRET", secrets.token_hex(32))
# Login: Passwort-Hash aus Umgebungsvariable (vom Setup gesetzt)
APP_USER = os.environ.get("FELDNETZ_USER", "admin")
APP_PASS = os.environ.get("FELDNETZ_PASS", "")  # MUSS gesetzt sein


def login_required(f):
    @functools.wraps(f)
    def wrap(*a, **k):
        if not session.get("auth"):
            return redirect(url_for("login"))
        return f(*a, **k)
    return wrap


def load_cfg():
    with open(YAML, encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_sites(sites):
    cfg = load_cfg()
    cfg["sites"] = sites
    with open(YAML, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)


def autofill(sites):
    """Vergibt site_index + lan_subnet automatisch, wo leer (wie excel_to_yaml)."""
    SIR = list(ipaddress.ip_network("192.168.80.0/24").subnets(new_prefix=28))
    FZG = list(ipaddress.ip_network("192.168.81.0/24").subnets(new_prefix=27))
    used_idx = {int(s["site_index"]) for s in sites
                if str(s.get("site_index", "")).strip()}
    used_net = {str(s.get("lan_subnet", "")).strip() for s in sites
                if str(s.get("lan_subnet", "")).strip()}
    sir_idx, fzg_idx, si, fi = 11, 31, 0, 0
    for s in sites:
        prof = s.get("profile", "sirene")
        if not str(s.get("site_index", "")).strip():
            if prof == "sirene":
                while sir_idx in used_idx: sir_idx += 1
                s["site_index"] = sir_idx; used_idx.add(sir_idx)
            else:
                while fzg_idx in used_idx: fzg_idx += 1
                s["site_index"] = fzg_idx; used_idx.add(fzg_idx)
        else:
            s["site_index"] = int(s["site_index"])
        if not str(s.get("lan_subnet", "")).strip():
            pool = SIR if prof == "sirene" else FZG
            ptr = si if prof == "sirene" else fi
            while str(pool[ptr]) in used_net: ptr += 1
            s["lan_subnet"] = str(pool[ptr]); used_net.add(str(pool[ptr]))
            if prof == "sirene": si = ptr + 1
            else: fi = ptr + 1
    return sites


def validate(sites):
    """Gibt Liste von Fehlertexten zurueck (leer = ok). Erwartet gefuellte Felder."""
    errs, names, idxs, nets = [], set(), set(), []
    for s in sites:
        n = str(s.get("name", "")).strip()
        if not n:
            errs.append("Ein Standort hat keinen Namen.")
            continue
        if s.get("profile") not in VALID_PROFILES:
            errs.append(f"{n}: Profil ungueltig.")
        if n in names:
            errs.append(f"Doppelter Name: {n}")
        names.add(n)
        try:
            i = int(s["site_index"])
            if i in idxs:
                errs.append(f"Doppelter site_index: {i} ({n})")
            idxs.add(i)
        except (ValueError, TypeError, KeyError):
            errs.append(f"{n}: site_index fehlt/ungueltig.")
        try:
            net = ipaddress.ip_network(s["lan_subnet"], strict=True)
            for pn, pnet in nets:
                if net.overlaps(pnet):
                    errs.append(f"Subnetz-Ueberlappung: {n} mit {pn}")
            nets.append((n, net))
        except (ValueError, KeyError):
            errs.append(f"{n}: lan_subnet fehlt/ungueltig.")
    return errs


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if (request.form.get("user") == APP_USER and
                APP_PASS and request.form.get("pass") == APP_PASS):
            session["auth"] = True
            return redirect(url_for("index"))
        flash("Login fehlgeschlagen.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    cfg = load_cfg()
    return render_template("index.html", sites=cfg["sites"],
                           anchors=cfg["anchors"], profiles=VALID_PROFILES)


@app.route("/save", methods=["POST"])
@login_required
def save():
    data = request.get_json()
    sites = autofill(data.get("sites", []))
    errs = validate(sites)
    if errs:
        return jsonify(ok=False, errors=errs)
    save_sites(sites)
    return jsonify(ok=True)


@app.route("/generate", methods=["POST"])
@login_required
def generate():
    # build.sh ausfuehren (Excel-Schritt uebersprungen - YAML ist schon aktuell)
    try:
        subprocess.run(["python3", "anker_keys.py"], cwd=BASE, check=True,
                       capture_output=True, text=True)
        r = subprocess.run(["python3", "generate.py"], cwd=BASE, check=True,
                           capture_output=True, text=True)
        return jsonify(ok=True, log=r.stdout)
    except subprocess.CalledProcessError as e:
        return jsonify(ok=False, log=(e.stdout or "") + (e.stderr or ""))


@app.route("/download")
@login_required
def download():
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(OUT):
            for fn in files:
                p = os.path.join(root, fn)
                z.write(p, os.path.relpath(p, BASE))
    mem.seek(0)
    name = f"feldnetz-configs-{datetime.now():%Y%m%d-%H%M}.zip"
    return send_file(mem, as_attachment=True, download_name=name,
                     mimetype="application/zip")



@app.route("/rms/token", methods=["POST"])
@login_required
def rms_token():
    """RMS-API-Token verschluesselt auf dem Anker ablegen."""
    token = (request.get_json() or {}).get("token", "").strip()
    if not token:
        return jsonify(ok=False, msg="Kein Token angegeben.")
    if not os.environ.get("FELDNETZ_MASTER"):
        return jsonify(ok=False, msg="FELDNETZ_MASTER nicht gesetzt - Server kann nicht verschluesseln.")
    try:
        sys.path.insert(0, BASE)
        import keystore
        keystore.save_token(token)
        return jsonify(ok=True, msg="Token verschluesselt gespeichert.")
    except Exception as e:
        return jsonify(ok=False, msg=str(e))


@app.route("/rms/status")
@login_required
def rms_status():
    try:
        sys.path.insert(0, BASE)
        import keystore
        return jsonify(has_token=keystore.has_token())
    except Exception:
        return jsonify(has_token=False)


@app.route("/rms/discover")
@login_required
def rms_discover():
    """Geraete aus RMS lesen und als JSON zurueck."""
    try:
        r = _sp.run(["python3", "push_rms.py", "--discover"], cwd=BASE,
                    capture_output=True, text=True, timeout=60,
                    env=dict(os.environ))
        return jsonify(ok=r.returncode == 0, output=r.stdout + r.stderr)
    except Exception as e:
        return jsonify(ok=False, output=str(e))


def active_anchor_ids():
    """IDs der aktiven Anker aus der YAML (fuer Auto-Sync)."""
    try:
        cfg = load_cfg()
        return [a["id"] for a in cfg.get("anchors", []) if a.get("active")]
    except Exception:
        return []


def sync_anchors():
    """Ruft sync_anker.sh je aktivem Anker auf (per sudo, eng begrenzt).
    Gibt (ok, log) zurueck. Fehlt das Skript/sudo, wird das gemeldet,
    aber der Push selbst gilt trotzdem als erfolgreich."""
    script = os.path.join(BASE, "sync_anker.sh")
    if not os.path.exists(script):
        return True, "(Auto-Sync uebersprungen: sync_anker.sh nicht vorhanden)"
    logs = []
    all_ok = True
    for aid in (active_anchor_ids() or ["a1"]):
        try:
            r = _sp.run(["sudo", "-n", script, aid], cwd=BASE,
                        capture_output=True, text=True, timeout=60)
            logs.append(f"[sync {aid}] {(r.stdout + r.stderr).strip()}")
            if r.returncode != 0:
                all_ok = False
        except Exception as e:
            logs.append(f"[sync {aid}] FEHLER: {e}")
            all_ok = False
    return all_ok, "\n".join(logs)


@app.route("/rms/push", methods=["POST"])
@login_required
def rms_push():
    """Configs pushen. dry=true -> nur Anzeige.
    Bei scharfem Push werden danach die Anker-Peers automatisch synchronisiert."""
    dry = (request.get_json() or {}).get("dry", True)
    cmd = ["python3", "push_rms.py"]
    if not dry:
        cmd.append("--apply")
    try:
        r = _sp.run(cmd, cwd=BASE, capture_output=True, text=True,
                    timeout=300, env=dict(os.environ))
        out = r.stdout + r.stderr
        ok = r.returncode == 0
        # Nach erfolgreichem SCHARFEN Push: Anker-Peers automatisch laden
        if ok and not dry:
            sync_ok, sync_log = sync_anchors()
            out += "\n\n--- Anker-Synchronisierung ---\n" + sync_log
            if not sync_ok:
                out += ("\n\nHinweis: Push war erfolgreich, aber die automatische "
                        "Anker-Synchronisierung hat nicht (vollstaendig) geklappt. "
                        "Ggf. einmalig sudo-Rechte einrichten (siehe SETUP-WEBAPP.md).")
        return jsonify(ok=ok, output=out)
    except Exception as e:
        return jsonify(ok=False, output=str(e))



@app.route("/rms/devices")
@login_required
def rms_devices():
    """Geraeteliste aus RMS als JSON, optional ?prefix=GW-Mess."""
    prefix = request.args.get("prefix", "").strip()
    cmd = ["python3", "push_rms.py", "--discover-json"]
    if prefix:
        cmd += ["--prefix", prefix]
    try:
        r = _sp.run(cmd, cwd=BASE, capture_output=True, text=True,
                    timeout=60, env=dict(os.environ))
        # letzte nicht-leere Zeile ist das JSON
        lines = [l for l in r.stdout.strip().splitlines() if l.strip()]
        data = json.loads(lines[-1]) if lines else []
        return jsonify(ok=True, devices=data)
    except Exception as e:
        return jsonify(ok=False, msg=str(e), devices=[])


@app.route("/rms/import", methods=["POST"])
@login_required
def rms_import():
    """Angehakte Router als Standorte uebernehmen (Typ je Router)."""
    sel = (request.get_json() or {}).get("selection", [])
    # sel: [{name, type}] mit type in sirene|fahrzeug
    cfg = load_cfg()
    existing = {s["name"].lower() for s in cfg["sites"]}
    added = 0
    new_sites = list(cfg["sites"])
    for item in sel:
        nm = str(item.get("name", "")).strip()
        typ = item.get("type")
        if not nm or typ not in ("sirene", "fahrzeug"):
            continue
        if nm.lower() in existing:
            continue
        new_sites.append({"name": nm, "profile": typ})  # Index/Subnetz: auto
        existing.add(nm.lower())
        added += 1
    # autofill + validate + speichern
    new_sites = autofill(new_sites)
    errs = validate(new_sites)
    if errs:
        return jsonify(ok=False, msg="Validierung: " + "; ".join(errs))
    save_sites(new_sites)
    return jsonify(ok=True, added=added, total=len(new_sites))


if __name__ == "__main__":
    if not APP_PASS:
        raise SystemExit("FELDNETZ_PASS nicht gesetzt - Abbruch (kein Login moeglich).")
    # NUR auf interner IP lauschen lassen - via Setup an VPN-IP binden
    app.run(host=os.environ.get("FELDNETZ_BIND", "127.0.0.1"),
            port=int(os.environ.get("FELDNETZ_PORT", "8080")))
