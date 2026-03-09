#!/usr/bin/env python3
"""
🌱 Raspberry Pi Frühjahrsputz
Automatisches Aufräum-Script für deinen Raspi
"""

import subprocess
import shutil
import os
import sys
from pathlib import Path


# ANSI Farben
class C:
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[94m"
    BLUE   = "\033[94m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"
    CYAN   = "\033[96m"


def header():
    print(f"""
{C.GREEN}{C.BOLD}
  🌸  Raspberry Pi Frühjahrsputz  🌸
{'─' * 40}{C.RESET}
""")


def run(cmd, capture=True):
    """Führt einen Shell-Befehl aus."""
    result = subprocess.run(
        cmd, shell=True, capture_output=capture, text=True
    )
    return (result.stdout.strip() if result.stdout else ""), result.returncode


def section(title):
    print(f"\n{C.CYAN}{C.BOLD}▶ {title}{C.RESET}")
    print("─" * 40)


def ok(msg):
    print(f"  {C.GREEN}✓{C.RESET} {msg}")

def warn(msg):
    print(f"  {C.YELLOW}⚠{C.RESET}  {msg}")

def info(msg):
    print(f"  {C.BLUE}i{C.RESET} {msg}")


# ─── 1. SYSTEM INFO ──────────────────────────────────────────────────────────

def show_system_info():
    section("Systemübersicht")

    # Temperatur
    temp_out, _ = run("vcgencmd measure_temp 2>/dev/null")
    if temp_out:
        temp_val = temp_out.replace("temp=", "")
        ok(f"CPU-Temperatur: {temp_val}")
    else:
        info("vcgencmd nicht verfügbar (kein Raspi?)")

    # Uptime
    uptime, _ = run("uptime -p")
    ok(f"Laufzeit: {uptime}")

    # RAM
    mem, _ = run("free -h | awk '/^Mem/ {print $3\"/\"$2}'")
    ok(f"RAM genutzt: {mem}")

    # Speicherplatz
    disk, _ = run("df -h / | awk 'NR==2 {print $3\"/\"$2\" (\"$5\" belegt)\"}'")
    ok(f"Speicher /: {disk}")


# ─── 2. SYSTEM UPDATE ────────────────────────────────────────────────────────

def update_system():
    section("System-Update")

    if os.geteuid() != 0:
        warn("Nicht als root – Update wird übersprungen (führe script mit sudo aus)")
        return

    print("  Aktualisiere Paketliste...")
    _, rc = run("apt-get update -qq", capture=False)
    if rc == 0:
        ok("Paketliste aktualisiert")

    print("  Installiere Updates...")
    _, rc = run("DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -qq", capture=False)
    if rc == 0:
        ok("Pakete aktualisiert")

    print("  Entferne verwaiste Pakete...")
    _, rc = run("apt-get autoremove -y -qq", capture=False)
    ok("autoremove erledigt")

    run("apt-get autoclean -qq")
    ok("apt-Cache geleert")


# ─── 3. JOURNAL LOGS ─────────────────────────────────────────────────────────

def clean_journal():
    section("Journal-Logs aufräumen")

    size_before, _ = run("journalctl --disk-usage 2>/dev/null | awk '{print $NF}'")
    info(f"Log-Größe vorher: {size_before or 'unbekannt'}")

    if os.geteuid() == 0:
        run("journalctl --vacuum-time=30d")
        run("journalctl --vacuum-size=100M")
        size_after, _ = run("journalctl --disk-usage 2>/dev/null | awk '{print $NF}'")
        ok(f"Logs bereinigt. Größe jetzt: {size_after or 'unbekannt'}")
    else:
        warn("Root-Rechte benötigt – übersprungen")


# ─── 4. TEMP & CACHES ────────────────────────────────────────────────────────

def clean_temp():
    section("Temp-Dateien & Caches")

    cleaned = 0
    for tmp_dir in ["/tmp", "/var/tmp"]:
        p = Path(tmp_dir)
        if p.exists():
            files = list(p.iterdir())
            if os.geteuid() == 0:
                for f in files:
                    try:
                        if f.is_file() or f.is_symlink():
                            f.unlink()
                        elif f.is_dir():
                            shutil.rmtree(f)
                        cleaned += 1
                    except Exception:
                        pass
            info(f"{tmp_dir}: {len(files)} Einträge gefunden")

    if os.geteuid() == 0:
        ok(f"{cleaned} Temp-Dateien entfernt")
    else:
        warn("Root-Rechte benötigt – Temp-Bereinigung übersprungen")

    # pip cache
    pip_cache, _ = run("pip cache info 2>/dev/null | grep 'Location' | awk '{print $2}'")
    if pip_cache and Path(pip_cache).exists():
        size, _ = run(f"du -sh {pip_cache} | awk '{{print $1}}'")
        info(f"pip-Cache ({size}): mit 'pip cache purge' bereinigen")
    else:
        ok("Kein pip-Cache gefunden")


# ─── 5. LAUFENDE DIENSTE ─────────────────────────────────────────────────────

def check_services():
    section("Laufende Dienste")

    services, _ = run(
        "systemctl list-units --type=service --state=running --no-legend "
        "| awk '{print $1}' | head -20"
    )
    if services:
        for svc in services.splitlines():
            info(svc)
    else:
        warn("Dienste konnten nicht abgerufen werden")


# ─── 6. GROSSE DATEIEN ───────────────────────────────────────────────────────

def find_large_files():
    section("Größte Verzeichnisse (Top 10)")

    dirs, _ = run("du -sh /* 2>/dev/null | sort -rh | head -10")
    if dirs:
        for line in dirs.splitlines():
            info(line)
    else:
        warn("Konnte Verzeichnisgrößen nicht ermitteln")


# ─── 7. SSH KEYS ─────────────────────────────────────────────────────────────

def check_ssh():
    section("SSH-Keys prüfen")

    auth_file = Path.home() / ".ssh" / "authorized_keys"
    if auth_file.exists():
        lines = [l for l in auth_file.read_text().splitlines() if l.strip() and not l.startswith("#")]
        ok(f"{len(lines)} authorisierte Key(s) in {auth_file}")
        for i, line in enumerate(lines, 1):
            # Zeige nur den Key-Typ und Kommentar, nicht den Key selbst
            parts = line.split()
            label = f"{parts[0]} ... {parts[-1]}" if len(parts) >= 3 else parts[0]
            info(f"  [{i}] {label}")
    else:
        info("Keine authorized_keys Datei gefunden")


# ─── 8. FSCK MARKER ──────────────────────────────────────────────────────────

def offer_fsck():
    section("Dateisystem-Check")

    marker = Path("/forcefsck")
    info("Ein fsck beim nächsten Neustart kann SD-Karten-Fehler aufdecken.")
    if os.geteuid() == 0:
        ans = input("  fsck beim nächsten Boot erzwingen? [j/N] ").strip().lower()
        if ans == "j":
            marker.touch()
            ok("/forcefsck gesetzt – fsck läuft beim nächsten Neustart")
        else:
            info("Übersprungen")
    else:
        warn("Root-Rechte benötigt – übersprungen")


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    header()

    if os.geteuid() != 0:
        print(f"{C.YELLOW}Hinweis: Nicht als root gestartet.")
        print(f"Einige Schritte werden übersprungen.{C.RESET}")
        print(f"Für vollständigen Putz: {C.BOLD}sudo python3 {sys.argv[0]}{C.RESET}\n")

    show_system_info()
    update_system()
    clean_journal()
    clean_temp()
    check_services()
    find_large_files()
    check_ssh()
    offer_fsck()

    print(f"\n{C.GREEN}{C.BOLD}✅  Frühjahrsputz abgeschlossen!{C.RESET}\n")


if __name__ == "__main__":
    main()
