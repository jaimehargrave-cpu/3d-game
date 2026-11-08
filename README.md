# Neon Strike FPS

A standalone desktop first-person shooter built with Python and Ursina. This is not a browser app.

## Requirements and launch

- Python 3.10+
- pip

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python neon_strike.py
```

`neon_strike.py` is the game launcher. `main.py` is retained only as the original implementation file for backward compatibility.

## Controls

- **WASD** — move
- **Mouse** — look and aim
- **Left click** — fire
- **1 / 2** — switch pistol / rifle
- **R** — reload
- **Space** — jump
- **Esc** — pause / resume

## Features

- Start, pause, and game-over screens
- Pistol and rifle with separate magazines, reserve ammo, reload times, and fire rates
- Larger 120-by-120 arena with cover and landmarks
- Enemies that pursue, flank at close range, and try to navigate around obstacles
- Waves, score, health HUD, hit marker, and synthesized sound effects (no external sound files needed)

Survive each wave and keep your score climbing.
