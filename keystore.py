#!/usr/bin/env python3
"""
keystore.py - speichert den RMS-API-Token VERSCHLUESSELT auf dem Anker.

Verschluesselung: Fernet (AES-128) mit Schluessel aus einem Master-Passwort
(PBKDF2-HMAC-SHA256, 600k Iterationen). Der Token liegt NIE im Klartext.

Master-Passwort kommt aus der Umgebung FELDNETZ_MASTER (beim Start gesetzt),
NICHT mitgespeichert. Ohne Master-Passwort ist der Token nicht lesbar.

API:
  save_token(token)  -> verschluesselt nach secrets/rms_token.enc
  load_token()       -> entschluesselt (braucht FELDNETZ_MASTER)
"""
import base64, os, sys
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

HERE = os.path.dirname(os.path.abspath(__file__))
ENC = os.path.join(HERE, "secrets", "rms_token.enc")
SALT = os.path.join(HERE, "secrets", "rms_token.salt")


def _key(master: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32,
                     salt=salt, iterations=600_000)
    return base64.urlsafe_b64encode(kdf.derive(master.encode()))


def _master() -> str:
    m = os.environ.get("FELDNETZ_MASTER")
    if not m:
        raise RuntimeError("FELDNETZ_MASTER nicht gesetzt - Token nicht entsperrbar.")
    return m


def save_token(token: str):
    os.makedirs(os.path.dirname(ENC), exist_ok=True)
    salt = os.urandom(16)
    f = Fernet(_key(_master(), salt))
    with open(ENC, "wb") as fh:
        fh.write(f.encrypt(token.encode()))
    with open(SALT, "wb") as fh:
        fh.write(salt)
    os.chmod(ENC, 0o600)
    os.chmod(SALT, 0o600)


def load_token() -> str:
    if not (os.path.exists(ENC) and os.path.exists(SALT)):
        raise RuntimeError("Kein gespeicherter Token.")
    salt = open(SALT, "rb").read()
    f = Fernet(_key(_master(), salt))
    try:
        return f.decrypt(open(ENC, "rb").read()).decode()
    except InvalidToken:
        raise RuntimeError("Master-Passwort falsch - Token nicht entschluesselbar.")


def has_token() -> bool:
    return os.path.exists(ENC) and os.path.exists(SALT)


if __name__ == "__main__":
    # CLI: echo "token" | FELDNETZ_MASTER=... python3 keystore.py save
    if len(sys.argv) > 1 and sys.argv[1] == "save":
        tok = sys.stdin.read().strip()
        save_token(tok)
        print("Token verschluesselt gespeichert.")
    elif len(sys.argv) > 1 and sys.argv[1] == "show":
        print(load_token())
    else:
        print("Nutzung: keystore.py save|show")
