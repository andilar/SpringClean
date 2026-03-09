# 🌸 SpringClean for Raspbyerry Pi

A Python maintenance script for Raspberry Pi — cleans up your system in one run.

## Features

- 📊 System overview (CPU temp, RAM, disk usage)
- 📦 System update (`apt upgrade`, `autoremove`, `autoclean`)
- 📋 Journal log cleanup (vacuum by time & size)
- 🗑️ Temp & pip cache cleanup
- ⚙️ Running services overview
- 📁 Largest directories (Top 10)
- 🔑 SSH authorized keys audit
- 💾 Optional fsck on next boot

## Usage

### One-liner (download & run)

```bash
# Full cleanup (recommended):
curl -sSL https://raw.githubusercontent.com/andilar/SpringClean/main/spring_clean.py | sudo python3

# Read-only / inspect only:
curl -sSL https://raw.githubusercontent.com/andilar/SpringClean/main/spring_clean.py | python3
```

### Or download first, then run

```bash
curl -sSLO https://raw.githubusercontent.com/andilar/SpringClean/main/spring_clean.py
sudo python3 spring_clean.py
```

> Some steps (apt update, journal vacuum, temp cleanup) require root privileges.

## Requirements

- Python 3.6+
- Raspberry Pi OS (Debian-based) — or any Debian/Ubuntu system
- No external packages needed

## License

MIT
