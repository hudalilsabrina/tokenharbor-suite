#!/usr/bin/env python3
"""Batch runner untuk TokenHarbor Suite."""
import sys
import subprocess

count = int(sys.argv[1]) if len(sys.argv) > 1 else 5
print(f"Menjalankan batch harvest {count} akun TokenHarbor...")
cmd = [sys.executable, "main.py", "harvest", str(count)]
subprocess.run(cmd)
