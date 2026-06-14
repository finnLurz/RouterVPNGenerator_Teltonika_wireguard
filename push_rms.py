#!/usr/bin/env python3
"""
push_rms.py - Teltonika RMS Cloud API (v3, gegen offizielle OpenAPI gebaut).

Funktionen:
  --discover         Geraete aus RMS lesen (Modell, Status, Serial) -> Tabelle
  --map              Discovery + Vorschlag, welcher Router neu ist (nicht zugeordnet)
  (default)          Dry-Run: zeigt, welches *.uci.sh an welches Geraet ginge
  --apply            scharf: POST /devices/{id}/command je Geraet

Echte Endpunkte (aus compiled.yaml):
  GET  /devices                     -> data[]: id, model, name, serial, status...
  POST /devices/{id}/command        -> body {"command": "<shell>"}

Token: aus RMS_API_TOKEN (env) ODER verschluesselter Datei (siehe keystore.py).
2FA im RMS-Account ist Pflicht fuer Token-Erstellung.
"""
import argparse, json, os, sys, urllib.request, urllib.error, urllib.parse

RMS_BASE = os.environ.get("RMS_BASE", "https://rms.teltonika-networks.com/api")
HERE = os.path.dirname(os.path.abspath(__file__))
DEVICES_DIR = os.path.join(HERE, "out", "devices")

# Status-Codes laut Spec: 0 offline, 1 online, 2 pending
STATUS = {0: "offline", 1: "online", 2: "pending"}


def get_token():
    t = os.environ.get("RMS_API_TOKEN")
    if t:
        return t
    # Fallback: verschluesselte Datei via keystore
    try:
        import keystore
        return keystore.load_token()
    except Exception:
        sys.exit("Kein Token: RMS_API_TOKEN setzen oder keystore einrichten.")


def api(method, path, token, payload=None, params=None):
    url = RMS_BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode()[:300]}
    except urllib.error.URLError as e:
        return 0, {"error": str(e)}


def detect_series(model):
    m = (model or "").upper()
    if m.startswith("RUTX"): return "RUTXxx"
    if m.startswith("RUT9") or m.startswith("RUT95") or m.startswith("RUT96"): return "RUT9xx"
    if m.startswith("RUT2") or m.startswith("RUT24"): return "RUT2xx"
    return "?"


def fetch_devices(token):
    """Alle Geraete holen (paginiert)."""
    out, offset = [], 0
    while True:
        st, body = api("GET", "/devices", token,
                       params={"limit": 100, "offset": offset})
        if st != 200:
            sys.exit(f"GET /devices: HTTP {st} {body.get('error','')}")
        data = body.get("data", [])
        out.extend(data)
        if len(data) < 100:
            break
        offset += 100
    return out


def local_scripts():
    if not os.path.isdir(DEVICES_DIR):
        sys.exit("Keine Skripte. Erst ./build.sh ausfuehren.")
    return {fn[:-len(".uci.sh")]: os.path.join(DEVICES_DIR, fn)
            for fn in os.listdir(DEVICES_DIR) if fn.endswith(".uci.sh")}


def cmd_discover(token):
    devs = fetch_devices(token)
    print(f"{len(devs)} Geraete in RMS:\n")
    print(f"{'ID':8} {'Name':16} {'Modell':12} {'Serie':8} {'Status':8} Serial")
    print("-" * 72)
    for d in sorted(devs, key=lambda x: str(x.get("name", ""))):
        print(f"{str(d.get('id','')):8} {str(d.get('name',''))[:16]:16} "
              f"{str(d.get('model',''))[:12]:12} {detect_series(d.get('model')):8} "
              f"{STATUS.get(d.get('status'),'?'):8} {d.get('serial','')}")
    return devs


def cmd_map(token):
    devs = fetch_devices(token)
    scripts = local_scripts()
    have = {s.lower() for s in scripts}
    print("Zuordnung RMS-Geraet -> lokaler Standort (Matching ueber Name):\n")
    unmatched = []
    for d in devs:
        nm = str(d.get("name", "")).lower()
        tag = "OK" if nm in have else "NEU (nicht zugeordnet)"
        if nm not in have:
            unmatched.append(d)
        print(f"  {str(d.get('name','')):16} {str(d.get('model','')):12} -> {tag}")
    if unmatched:
        print(f"\n{len(unmatched)} Router ohne Zuordnung. In der Weboberflaeche "
              f"als Sirene/Fahrzeug anlegen, dann ./build.sh + Push.")



def cmd_discover_json(token, prefix=None):
    """Geraete als JSON-Liste (fuer Weboberflaeche). Optional Namensfilter."""
    import json as _j
    devs = fetch_devices(token)
    rows = []
    for d in devs:
        nm = str(d.get("name", ""))
        if prefix and not nm.lower().startswith(prefix.lower()):
            continue
        rows.append({
            "id": d.get("id"),
            "name": nm,
            "model": d.get("model", ""),
            "series": detect_series(d.get("model")),
            "status": STATUS.get(d.get("status"), "?"),
            "serial": d.get("serial", ""),
        })
    rows.sort(key=lambda r: r["name"].lower())
    print(_j.dumps(rows))
    return rows


def cmd_diag(token, devname):
    """Fuehrt Diagnose-Befehle auf einem Geraet aus (per RMS-Command-API)."""
    devs = {str(d.get("name", "")).lower(): d for d in fetch_devices(token)}
    d = devs.get(devname.lower())
    if not d:
        sys.exit(f"{devname}: nicht in RMS gefunden.")
    if STATUS.get(d.get("status")) != "online":
        print(f"WARNUNG: {devname} ist {STATUS.get(d.get('status'))}, nicht online. "
              f"Diagnose kann fehlschlagen.")
    # Diagnose-Befehle gebuendelt mit Trennern fuer Lesbarkeit
    diag_cmd = (
        "echo '=== 1. MOBILFUNK ==='; "
        "ifstatus mob1s1a1 2>/dev/null | grep -E '\"up\"|\"address\"' || echo 'mob1s1a1 nicht gefunden'; "
        "echo '=== 2. APN ==='; "
        "uci -q get network.mob1s1a1.apn || echo 'kein APN gesetzt'; "
        "echo '=== 3. WIREGUARD INTERFACE ==='; "
        "wg show 2>/dev/null || echo 'wg nicht verfuegbar/laeuft nicht'; "
        "echo '=== 4. WG-CONFIG IN UCI ==='; "
        "uci show network 2>/dev/null | grep -E 'wg_a1|peer_a1' || echo 'keine wg_a1-Config'; "
        "echo '=== 5. INTERFACE-STATUS wg_a1 ==='; "
        "ifstatus wg_a1 2>/dev/null | grep -E '\"up\"' || echo 'wg_a1 nicht up'; "
        "echo '=== ENDE ==='"
    )
    print(f"Sende Diagnose an {devname} (RMS-ID {d['id']})...\n")
    st, body = api("POST", f"/devices/{d['id']}/command", token,
                   payload={"command": diag_cmd})
    print(f"HTTP {st}")
    print(json.dumps(body, indent=2, ensure_ascii=False))
    print("\nHINWEIS: Wenn die API nur eine Task-ID zurueckgibt, wird der Befehl "
          "asynchron ausgefuehrt. Die Ausgabe erscheint dann in RMS unter "
          "Task Manager / Results, nicht direkt hier.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--discover", action="store_true", help="Geraete auflisten")
    ap.add_argument("--discover-json", action="store_true", help="Geraete als JSON")
    ap.add_argument("--prefix", help="Namensfilter (beginnt mit)")
    ap.add_argument("--map", action="store_true", help="Zuordnung anzeigen")
    ap.add_argument("--only", help="nur dieser Standort")
    ap.add_argument("--apply", action="store_true", help="scharf senden")
    ap.add_argument("--diag", metavar="GERAET",
                    help="Diagnose-Befehle auf einem Geraet ausfuehren (per API)")
    args = ap.parse_args()
    token = get_token()

    if args.discover:
        return cmd_discover(token)
    if args.discover_json:
        return cmd_discover_json(token, args.prefix)
    if args.map:
        return cmd_map(token)
    if args.diag:
        return cmd_diag(token, args.diag)

    # Push-Modus
    scripts = local_scripts()
    if args.only:
        scripts = {k: v for k, v in scripts.items() if k == args.only}
        if not scripts:
            sys.exit(f"{args.only}: kein Skript.")
    devs = {str(d.get("name", "")).lower(): d for d in fetch_devices(token)}

    print(f"Modus: {'APPLY (scharf)' if args.apply else 'DRY-RUN'}\n")
    print(f"{'Standort':14} {'RMS-ID':8} {'Modell':12} {'Status':8} Aktion")
    print("-" * 64)
    plan = []
    for name, path in sorted(scripts.items()):
        d = devs.get(name.lower())
        if not d:
            print(f"{name:14} {'-':8} {'-':12} {'-':8} NICHT in RMS")
            continue
        stat = STATUS.get(d.get("status"), "?")
        if stat != "online":
            print(f"{name:14} {str(d['id']):8} {str(d.get('model',''))[:12]:12} {stat:8} uebersprungen (offline)")
            continue
        print(f"{name:14} {str(d['id']):8} {str(d.get('model',''))[:12]:12} {stat:8} {'SENDEN' if args.apply else 'wuerde senden'}")
        plan.append((name, d, path))

    if not args.apply:
        print(f"\nDRY-RUN: {len(plan)} Geraete. Scharf mit --apply")
        return

    print()
    ok = fail = 0
    for name, d, path in plan:
        cmd = open(path, encoding="utf-8").read()
        st, body = api("POST", f"/devices/{d['id']}/command", token,
                       payload={"command": cmd})
        if st in (200, 201, 202):
            ok += 1; print(f"  OK   {name}")
        else:
            fail += 1; print(f"  FEHL {name}: HTTP {st} {str(body.get('error',''))[:100]}")
    print(f"\nFertig: {ok} ok, {fail} fehlgeschlagen.")


if __name__ == "__main__":
    main()
