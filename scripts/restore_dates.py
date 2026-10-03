#!/usr/bin/env python3
"""Восстановить время изменения исходников из последнего коммита каждого файла."""
from pathlib import Path
import os
import subprocess

root = Path(__file__).resolve().parents[1]
paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
for name in filter(None, paths):
    path = root / name
    if path.suffix in {'.qmd', '.yml', '.css', '.svg', '.typ'}:
        value = subprocess.check_output(['git', 'log', '-1', '--format=%ct', '--', name], cwd=root).strip()
        if value:
            timestamp = int(value)
            os.utime(path, (timestamp, timestamp))
