# Architektur

## Überblick

Das Feldnetz verbindet entfernte Standorte (Sirenen, Fahrzeuge) über Mobilfunk
verschlüsselt mit der zentralen Feuerwehr-Infrastruktur. Jeder Standort hat einen
Teltonika-Router mit Mobilfunk-SIM. Da Mobilfunk hinter CGNAT liegt (keine
öffentliche IP), bauen die Router aktiv einen WireGuard-Tunnel zu einem zentralen
**Anker** auf.

```
  Standort (Sirene/Fahrzeug)                   Feuerwehr Mitte
  ┌────────────────────────┐                ┌──────────────────────┐
  │ Teltonika RUT241       │                │ Sophos Firewall      │
  │ - Mobilfunk (CGNAT)    │  WireGuard     │ 198.51.100.10         │
  │ - WireGuard-Client     │═══UDP 51821═══▶│ DNAT → Anker         │
  │ - Sirenen-NAT          │                │                      │
  └────────────────────────┘                │ Anker A (VM)         │
                                            │ 172.20.10.20         │
  Endpunkt-Name:                            │ - WireGuard wg-a1    │
  anker-a.vpn.example.org                     │ - BGP (FRR)          │
  (DDNS folgt aktiver Leitung)              │ - Watchdog           │
                                            └──────────┬───────────┘
                                                       │ BGP
                                                       ▼
                                            px003 (AS65003) → restl. Netz
```

## Adressierung

| Bereich | Netz | Aufteilung |
|---------|------|------------|
| Supernetz (alles) | `192.168.80.0/20` | – |
| Sirenen | `192.168.80.0/24` | je Standort ein `/28` |
| Fahrzeuge | `192.168.81.0/24` | je Standort ein `/27` |
| Tunnel-Transfer | `10.80.1.0/24` | Hub = `.254`, Router ab `.11` |

**Service-IP-Konvention:** Jeder Standort hat eine Service-IP = Netznummer + 2.

| Standort | Subnetz | Tunnel-IP | Service-IP |
|----------|---------|-----------|------------|
| sirene01 | `192.168.80.0/28` | `10.80.1.11` | `192.168.80.2` |
| Standort-02 | `192.168.80.16/28` | `10.80.1.12` | `192.168.80.18` |

## Komponenten

### Anker A (VM, 172.20.10.20)
Zentrale Gegenstelle. Läuft auf Proxmox-Host px103 in VLAN 900.

- **WireGuard `wg-a1`** (Port 51821): nimmt alle Router-Tunnel an.
- **FRR (BGP, AS65101)**: verteilt die erreichbaren Standort-Netze an px003 (AS65003).
- **Watchdog** (systemd-Timer): annonciert das `/28` eines Standorts per BGP erst,
  wenn dessen Tunnel einen **frischen Handshake** hat. Tote Tunnel werden nicht
  annonciert → kein Blackhole-Routing.
- **DDNS-Cron**: hält `anker-a.vpn.example.org` auf der aktiven WAN-IP.

### Sophos Firewall (198.51.100.10)
- **DNAT-Regel** `DNAT-WG-A1`: leitet UDP 51821 → Anker (172.20.10.20).
  „Originales Ziel = Beliebig", eingehende Schnittstellen StarLink **und** WAN_P2
  (für Failover über beide Leitungen).
- **WAN-Failover**: schaltet bei Ausfall von Vodafone automatisch auf Starlink.

### Teltonika-Router (RUT241)
- Mobilfunk über M2M-SIM (APN `wsim`).
- WireGuard-Client mit Endpunkt `anker-a.vpn.example.org`.
- **Sirenen-NAT (1:1)**: Die Sirenensteuerung hat intern fest `192.168.1.12`.
  Eine DNAT-Regel (`SIRENE-SVC`) übersetzt die Service-IP → `192.168.1.12`.
  Dadurch ist die Steuerung über die Service-IP erreichbar, ohne sie selbst
  umzukonfigurieren.

## Datenfluss bei Tunnelaufbau

1. Router fragt DNS: `anker-a.vpn.example.org` → `198.51.100.10` (öffentliches DNS).
2. Router sendet WireGuard-Pakete an `198.51.100.10:51821` (UDP).
3. Sophos-DNAT übersetzt Ziel → `172.20.10.20` (Anker).
4. Anker und Router führen WireGuard-Handshake aus → Tunnel steht.
5. Watchdog erkennt frischen Handshake → setzt Kernel-Route für das `/28`.
6. BGP annonciert das `/28` an px003 → Standort ist im ganzen Netz erreichbar.

## Failover-Mechanik

Die Router kennen **nur einen** Endpunkt-Namen. Die **Sophos** macht das
WAN-Failover (Vodafone → Starlink). Das **DDNS-Skript** aktualisiert
`anker-a.vpn.example.org` auf die jeweils aktive öffentliche IP. Bei Failover
folgt der DNS-Eintrag, die Router lösen den Namen neu auf und finden den Anker
wieder – ohne Eingriff, ohne Neukonfiguration der Router.

> Warum kein zweiter Tunnel pro Router? Siehe [ENTSCHEIDUNGEN.md](ENTSCHEIDUNGEN.md).
