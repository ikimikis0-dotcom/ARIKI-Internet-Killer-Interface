# ARIKI v9 — Internet Killer Interface

Sietové nástroje pre **Kali Linux** v jednom súbore — od monitoringu a testovania vlastnej siete až po záťažové testy webov. 39 funkcií, pool-engine, low-CPU dizajn.

```
 █████    ██████    ██        ██╗  ██   ██
██╔══██   ██╔══██   ██        ██║ ██╔   ██
███████   ██████╔   ██        █████╔╝   ██
██╔══██   ██╔══██   ██        ██╔═██╗   ██
██║  ██   ██║  ██   ██        ██║  ██   ██
╚═╝  ╚═   ╚═╝  ╚═   ╚═        ╚═╝  ╚═   ╚═
═══ ARIKI v9 · Internet Killer Interface ═══
```

## Na čo to je

ARIKI je všestranná sada sieťových nástrojov do terminálu:

- **Monitoring a diagnostika** — ping, traceroute, port scan, whois, DNS testy, bandwidth test, HTTP monitor/hlavičky
- **Pentest a prieskum** — skenovanie ciest webu, security audit hlavičiek, detekcia CMS, zbieranie subdomén, LAN sken s detekciou neznámych zariadení
- **Monitoring vlastných zariadení** — Device Watch cez ADB (notifikácie, poloha, screenshot, SMS, hovory, aplikácie...)
- **Simulácia návštevníkov** — Web Visitors generujú realistickú ľudskú prevádzku (rôzne prehliadače, referrery, cookies) pre testovanie cache a výkonu
- **Záťažové testy webov** — Cache-Buster, TLS handshake flood, API POST flood, Slowloris/RUDY a **AUTO KILL**, ktorý sám oskenuje web, vyberie vektory a zaútočí

> ⚠️ **Používaj len na vlastné zariadenia a siete, alebo s výslovným povolením vlastníka.**
> Útočné funkcie sú určené na testovanie zabezpečenia. Zodpovednosť za použitie je na tebe.

## Požiadavky

- Linux (odporúčané: **Kali Linux**)
- Python 3.8+
- `sudo` — väčšina funkcií vyžaduje root (raw sockety)
- Voliteľne: `playwright` (mód BROWSER v Web Visitors), `adb` (Device Watch)

## Inštalácia a spustenie

```bash
git clone 
cd 

# voliteľné závislosti
sudo apt install python3 python3-pip adb
pip3 install playwright          # len ak chceš Web Visitors v BROWSER móde
python3 -m playwright install    # a ich prehliadač

# spustenie
sudo python3 netlab.py
```

## Použitie

```bash
sudo python3 netlab.py
```

Vyber číslo z menu a stlač Enter. Príklady:

| Príklad | Význam |
|---|---|
| `27` | Traffic Generator — sám nájde otvorené porty a spustí všetky vektory naraz |
| `39` | **AUTO KILL** — oskenuje celý web, načíta cesty zo stránky a vyberie najlepší útok |
| `29` | Device Watch — sledovanie vlastného telefónu cez ADB |
| `30` | LAN Watch — skenovanie vlastnej siete s alarmom na neznáme zariadenia |
| `31–34` | Web Scanner, Security Audit, CMS Detect, Subdomain OSINT |
| `18` | Nastavenia (počet CPU, rate limit, ECO režim) |

## Funkcie (39)

**Sieť:** Ping, SYN Flood, TCP Port Scan, UDP Flood, HTTP/HTTPS Flood, Slowloris, DNS Flood, ICMP Flood, Traceroute, TCP Connect Flood, TCP ACK/FIN/RST, Multi-Target Flood, DNS Resolver Test, Whois, RUDY, ARP Flood, Ping Sweep, Bandwidth Test, SYN All Ports, Smurf

**Web testy:** HTTP Monitor, HTTP Headers, Web Scanner (enum), Security Audit, CMS Detect, Subdomain OSINT, Web Visitors (ludia)

**Web útoky:** Cache-Buster Flood, TLS Handshake Flood, API POST Flood, WEB KILL (crawl+flood), WEB KILL VSAKO, **AUTO KILL** (sken + výber vektorov)

**Device/LAN:** Device Watch (ADB), LAN Watch (siet), Traffic Generator (AUTO)

## Štruktúra

- `netlab.py` — celý nástroj (jeden súbor, žiadne závislosti okrem štandardnej knižnice)

## Licence

Pre osobnú a vzdelávaciu potrebu. Útočné funkcie sú výhradne na testovanie vlastných systémov.
