"""CSRF-Schutz der Web-Oberflaeche.

Aufruf (aus dem Repo-Wurzelverzeichnis, venv mit webapp/requirements.txt):
    python3 -m unittest discover -s webapp -p 'test_*.py' -v
"""
import os
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock

os.environ["FELDNETZ_USER"] = "tester"
os.environ["FELDNETZ_PASS"] = "Pässwort-Test"
os.environ.pop("FELDNETZ_HTTPS", None)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as webapp  # noqa: E402

POST_ROUTES = ["/save", "/generate", "/rms/token", "/rms/push", "/rms/import"]


def token_aus(html):
    m = re.search(r'(?:name="csrf_token" value|name="csrf-token" content)="([^"]+)"', html)
    return m.group(1) if m else None


class CsrfTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        yaml_kopie = os.path.join(self.tmp, "standorte.yaml")
        shutil.copy(webapp.YAML, yaml_kopie)
        self.yaml_patch = mock.patch.object(webapp, "YAML", yaml_kopie)
        self.yaml_patch.start()
        webapp.app.config["TESTING"] = True
        self.c = webapp.app.test_client()

    def tearDown(self):
        self.yaml_patch.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def login(self):
        tok = token_aus(self.c.get("/login").get_data(as_text=True))
        self.assertTrue(tok)
        r = self.c.post("/login", data={"user": "tester", "pass": "Pässwort-Test",
                                        "csrf_token": tok})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.headers["Location"].endswith("/"))
        tok = token_aus(self.c.get("/").get_data(as_text=True))
        self.assertTrue(tok)
        return tok

    # --- Login -----------------------------------------------------------
    def test_login_ohne_token_abgewiesen(self):
        self.c.get("/login")
        r = self.c.post("/login", data={"user": "tester", "pass": "Pässwort-Test"})
        self.assertEqual(r.status_code, 400)
        with self.c.session_transaction() as s:
            self.assertFalse(s.get("auth"))

    def test_login_falsches_token_abgewiesen(self):
        self.c.get("/login")
        r = self.c.post("/login", data={"user": "tester", "pass": "Pässwort-Test",
                                        "csrf_token": "falsch"})
        self.assertEqual(r.status_code, 400)

    def test_login_falsches_passwort(self):
        tok = token_aus(self.c.get("/login").get_data(as_text=True))
        r = self.c.post("/login", data={"user": "tester", "pass": "nein",
                                        "csrf_token": tok})
        self.assertEqual(r.status_code, 200)
        with self.c.session_transaction() as s:
            self.assertFalse(s.get("auth"))

    def test_login_erneuert_token(self):
        alt = token_aus(self.c.get("/login").get_data(as_text=True))
        neu = self.login()
        self.assertNotEqual(alt, neu)

    # --- POST-Routen nach dem Login --------------------------------------
    def test_post_ohne_token_abgewiesen(self):
        self.login()
        # subprocess und _sp sind dasselbe Modul - ein Patch deckt beide ab
        with mock.patch.object(webapp.subprocess, "run") as run:
            for pfad in POST_ROUTES:
                r = self.c.post(pfad, json={})
                self.assertEqual(r.status_code, 400, pfad)
                self.assertFalse(r.get_json()["ok"], pfad)
            run.assert_not_called()

    def test_post_falsches_token_abgewiesen(self):
        self.login()
        with mock.patch.object(webapp._sp, "run") as run:
            for pfad in POST_ROUTES:
                r = self.c.post(pfad, json={}, headers={"X-CSRF-Token": "falsch"})
                self.assertEqual(r.status_code, 400, pfad)
            run.assert_not_called()

    def test_fremde_sitzung_token_gilt_nicht(self):
        fremd = webapp.app.test_client()
        fremd_tok = token_aus(fremd.get("/login").get_data(as_text=True))
        self.login()
        r = self.c.post("/save", json={"sites": []},
                        headers={"X-CSRF-Token": fremd_tok})
        self.assertEqual(r.status_code, 400)

    def test_save_mit_token(self):
        tok = self.login()
        sites = webapp.load_cfg()["sites"]
        r = self.c.post("/save", json={"sites": sites},
                        headers={"X-CSRF-Token": tok})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["ok"], r.get_json())

    def test_import_mit_token(self):
        tok = self.login()
        r = self.c.post("/rms/import",
                        json={"selection": [{"name": "csrf-test-sirene", "type": "sirene"}]},
                        headers={"X-CSRF-Token": tok})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["added"], 1)
        namen = [s["name"] for s in webapp.load_cfg()["sites"]]
        self.assertIn("csrf-test-sirene", namen)

    def test_push_mit_token_erreicht_handler(self):
        tok = self.login()
        fertig = mock.Mock(returncode=0, stdout="probelauf", stderr="")
        with mock.patch.object(webapp._sp, "run", return_value=fertig) as run:
            r = self.c.post("/rms/push", json={"dry": True},
                            headers={"X-CSRF-Token": tok})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["ok"])
        self.assertNotIn("--apply", run.call_args[0][0])

    def test_generate_mit_token_erreicht_handler(self):
        tok = self.login()
        fertig = mock.Mock(returncode=0, stdout="ok", stderr="")
        with mock.patch.object(webapp.subprocess, "run", return_value=fertig):
            r = self.c.post("/generate", headers={"X-CSRF-Token": tok})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["ok"])

    def test_token_ohne_login_reicht_nicht(self):
        tok = token_aus(self.c.get("/login").get_data(as_text=True))
        r = self.c.post("/save", json={"sites": []}, headers={"X-CSRF-Token": tok})
        self.assertEqual(r.status_code, 302)

    # --- Cookie-Einstellungen -------------------------------------------
    def test_cookie_flags(self):
        r = self.c.get("/login")
        cookie = r.headers.get("Set-Cookie", "")
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)
        self.assertNotIn("Secure", cookie)


if __name__ == "__main__":
    unittest.main()
