#!/usr/bin/env python3
"""Kill old uvicorn and restart"""
import subprocess, time, os, signal

# Kill uvicorn
result = subprocess.run(['pgrep', '-f', 'uvicorn'], capture_output=True, text=True)
pids = [int(p) for p in result.stdout.strip().split('\n') if p]
for pid in pids:
    try:
        os.kill(pid, signal.SIGTERM)
        print(f'Killed PID {pid}')
    except:
        pass

time.sleep(2)

# Clear cache
cache_dir = os.path.expanduser('~/fund_quant_app/backend/data')
for f in os.listdir(cache_dir):
    os.remove(os.path.join(cache_dir, f))

print('Cache cleared')
print('Ready to restart')
