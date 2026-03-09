#!/usr/bin/env python3
"""
🌱 SpringClean — Raspberry Pi Maintenance Script
Automated cleanup and health check for your Raspi
"""

import subprocess
import shutil
import os
import sys
from pathlib import Path


# ANSI colors
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
  🌸  SpringClean — Raspberry Pi Maintenance  🌸
{'─' * 48}{C.RESET}
""")


def run(cmd, capture=True):
    """Run a shell command."""
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
    section("System Overview")

    temp_out, _ = run("vcgencmd measure_temp 2>/dev/null")
    if temp_out:
        temp_val = temp_out.replace("temp=", "")
        ok(f"CPU temperature: {temp_val}")
    else:
        info("vcgencmd not available (not a Raspi?)")

    uptime, _ = run("uptime -p")
    ok(f"Uptime: {uptime}")

    mem, _ = run("free -h | awk '/^Mem/ {print $3\"/\"$2}'")
    ok(f"RAM used: {mem}")

    disk, _ = run("df -h / | awk 'NR==2 {print $3\"/\"$2\" (\"$5\" used)\"}'")
    ok(f"Disk /: {disk}")


# ─── 2. SYSTEM UPDATE ────────────────────────────────────────────────────────

def update_system():
    section("System Update")

    if os.geteuid() != 0:
        warn("Not running as root — skipping update (run script with sudo)")
        return

    print("  Updating package list...")
    _, rc = run("apt-get update -qq", capture=False)
    if rc == 0:
        ok("Package list updated")

    print("  Installing updates...")
    _, rc = run("DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -qq", capture=False)
    if rc == 0:
        ok("Packages upgraded")

    print("  Removing orphaned packages...")
    _, rc = run("apt-get autoremove -y -qq", capture=False)
    ok("autoremove done")

    run("apt-get autoclean -qq")
    ok("apt cache cleaned")


# ─── 3. JOURNAL LOGS ─────────────────────────────────────────────────────────

def clean_journal():
    section("Journal Log Cleanup")

    size_before, _ = run("journalctl --disk-usage 2>/dev/null | awk '{print $NF}'")
    info(f"Log size before: {size_before or 'unknown'}")

    if os.geteuid() == 0:
        run("journalctl --vacuum-time=30d")
        run("journalctl --vacuum-size=100M")
        size_after, _ = run("journalctl --disk-usage 2>/dev/null | awk '{print $NF}'")
        ok(f"Logs cleaned. Size now: {size_after or 'unknown'}")
    else:
        warn("Root privileges required — skipped")


# ─── 4. TEMP & CACHES ────────────────────────────────────────────────────────

def clean_temp():
    section("Temp Files & Caches")

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
            info(f"{tmp_dir}: {len(files)} entries found")

    if os.geteuid() == 0:
        ok(f"{cleaned} temp files removed")
    else:
        warn("Root privileges required — temp cleanup skipped")

    pip_cache, _ = run("pip cache info 2>/dev/null | grep 'Location' | awk '{print $2}'")
    if pip_cache and Path(pip_cache).exists():
        size, _ = run(f"du -sh {pip_cache} | awk '{{print $1}}'")
        info(f"pip cache ({size}): clean with 'pip cache purge'")
    else:
        ok("No pip cache found")


# ─── 5. RUNNING SERVICES ─────────────────────────────────────────────────────

def check_services():
    section("Running Services")

    services, _ = run(
        "systemctl list-units --type=service --state=running --no-legend "
        "| awk '{print $1}' | head -20"
    )
    if services:
        for svc in services.splitlines():
            info(svc)
    else:
        warn("Could not retrieve service list")


# ─── 6. LARGEST DIRECTORIES ──────────────────────────────────────────────────

def find_large_files():
    section("Largest Directories (Top 10)")

    dirs, _ = run("du -sh /* 2>/dev/null | sort -rh | head -10")
    if dirs:
        for line in dirs.splitlines():
            info(line)
    else:
        warn("Could not determine directory sizes")


# ─── 7. SSH KEYS ─────────────────────────────────────────────────────────────

def check_ssh():
    section("SSH Key Audit")

    auth_file = Path.home() / ".ssh" / "authorized_keys"
    if auth_file.exists():
        lines = [l for l in auth_file.read_text().splitlines() if l.strip() and not l.startswith("#")]
        ok(f"{len(lines)} authorized key(s) in {auth_file}")
        for i, line in enumerate(lines, 1):
            parts = line.split()
            label = f"{parts[0]} ... {parts[-1]}" if len(parts) >= 3 else parts[0]
            info(f"  [{i}] {label}")
    else:
        info("No authorized_keys file found")


# ─── 8. FSCK MARKER ──────────────────────────────────────────────────────────

def offer_fsck():
    section("Filesystem Check")

    marker = Path("/forcefsck")
    info("Running fsck on next boot can detect SD card errors.")
    if os.geteuid() == 0:
        try:
            with open("/dev/tty") as tty:
                sys.stdout.write("  Force fsck on next boot? [y/N] ")
                sys.stdout.flush()
                ans = tty.readline().strip().lower()
        except OSError:
            ans = ""
        if ans == "y":
            marker.touch()
            ok("/forcefsck set — fsck will run on next reboot")
        else:
            info("Skipped")
    else:
        warn("Root privileges required — skipped")


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    header()

    if os.geteuid() != 0:
        print(f"{C.YELLOW}Note: Not running as root.")
        print(f"Some steps will be skipped.{C.RESET}")
        print(f"For a full cleanup run: {C.BOLD}sudo python3 {sys.argv[0]}{C.RESET}\n")

    show_system_info()
    update_system()
    clean_journal()
    clean_temp()
    check_services()
    find_large_files()
    check_ssh()
    offer_fsck()

    print(f"\n{C.GREEN}{C.BOLD}✅  SpringClean complete!{C.RESET}\n")


if __name__ == "__main__":
    main()
