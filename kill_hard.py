#!/usr/bin/env python3
"""Kill everything on ports 8000 and 8001 with maximum force"""
import subprocess, os, signal, time

# Get all python processes
result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=10)
lines = result.stdout.strip().split('\n')
for line in lines:
    if 'uvicorn' in line.lower() or 'backend.main' in line:
        parts = line.split()
        if len(parts) >= 2:
            try:
                pid = int(parts[1])
                os.kill(pid, signal.SIGKILL)
                print(f'Killed {pid}: {line[:80]}')
            except:
                pass

time.sleep(2)
print('Done')
