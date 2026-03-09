# 🌸 SpringClean

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

```bash
# Full cleanup (recommended):
sudo python3 spring_clean.py

# Read-only / inspect only:
python3 spring_clean.py
```

> Some steps (apt update, journal vacuum, temp cleanup) require root privileges.

## Requirements

- Python 3.6+
- Raspberry Pi OS (Debian-based) — or any Debian/Ubuntu system
- No external packages needed

## License

MIT
