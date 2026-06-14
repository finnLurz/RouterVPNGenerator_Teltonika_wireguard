#!/usr/bin/env python3
"""
anker_keys.py - erzeugt Anker-Privkeys zentral und traegt die Pubkeys
automatisch in standorte.yaml ein. Idempotent: vorhandene Keys bleiben.

Privkeys liegen unter out/keys/anker.<id>.priv (chmod 600),
Pubkeys werden in anchors[].hub_public_key geschrieben.
Ausserdem out/anker/<id>.privkey fuer das VM-Rollout.
"""
import os, subprocess, sys
try:
    import yaml
except ImportError:
    sys.exit("pip install pyyaml")

HERE=os.path.dirname(os.path.abspath(__file__))
KEYS=os.path.join(HERE,"out","keys"); ANK=os.path.join(HERE,"out","anker")
YAML=os.path.join(HERE,"standorte.yaml")

def keypair(aid):
    os.makedirs(KEYS,exist_ok=True); os.makedirs(ANK,exist_ok=True)
    pv=os.path.join(KEYS,f"anker.{aid}.priv"); pb=os.path.join(KEYS,f"anker.{aid}.pub")
    if os.path.exists(pv) and os.path.exists(pb):
        priv,pub=open(pv).read().strip(),open(pb).read().strip()
    else:
        priv=subprocess.run(["wg","genkey"],capture_output=True,text=True).stdout.strip()
        pub=subprocess.run(["wg","pubkey"],input=priv,capture_output=True,text=True).stdout.strip()
        open(pv,"w").write(priv+"\n"); os.chmod(pv,0o600); open(pb,"w").write(pub+"\n")
    # privkey-Datei fuers VM-Rollout
    p=os.path.join(ANK,f"{aid}.privkey"); open(p,"w").write(priv+"\n"); os.chmod(p,0o600)
    return pub

def main():
    c=yaml.safe_load(open(YAML))
    changed=0
    for a in c["anchors"]:
        pub=keypair(a["id"])
        if a.get("hub_public_key")!=pub:
            a["hub_public_key"]=pub; changed+=1
        print(f"  {a['id']}: hub_public_key = {pub}")
    yaml.safe_dump(c,open(YAML,"w"),allow_unicode=True,sort_keys=False)
    print(f"OK: Anker-Pubkeys in standorte.yaml ({changed} aktualisiert).")
    print("Privkeys fuers VM-Rollout: out/anker/<id>.privkey")

if __name__=="__main__": main()
