# Geräte-Modelle (Teltonika)

Pro Familie eine YAML, die die modell-spezifischen UCI-Eigenheiten kennt.
Neues Modell unterstützen = neue Datei hier anlegen, kein Code-Umbau.

Felder:
  series        : RMS-Serie (fuer API-Gruppierung/Pruefung)
  wg_proto      : UCI-Proto fuer WireGuard-Interface (i.d.R. 'wireguard')
  lan_iface     : Name des LAN-Interfaces in UCI (meist 'lan')
  has_wifi      : ob WLAN-Abschaltung sinnvoll ist (RUTX/RUT9 = ja)
  notes         : Hinweise
