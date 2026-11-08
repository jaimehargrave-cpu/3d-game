"""Launcher for the Neon Strike desktop FPS.

Run with: python neon_strike.py
The game implementation is kept in main.py for backward compatibility.
"""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name('main.py')), run_name='__main__')
