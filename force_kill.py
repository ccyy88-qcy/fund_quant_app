#!/usr/bin/env python3
"""Force kill everything on port 8000"""
import subprocess, time, os, signal

# Kill ALL uvicorn and python processes that might hold the port
result = subprocess.run(['pgrep', '-f', 'python'], capture_output=True, text=True, timeout=10)
current_pid = os.getpid()
for p in result.stdout.strip().split('\n'):
    p = p.strip()
    if not p:
        continue
    pid = int(p)
    if pid == current_pid or pid == current_pid or pid <= 1:
        continue
    try:
        # Check if this process has port 8000 open
        proc_cmd = open(f'/proc/{pid}/cmdline', 'r').read() if os.path.exists(f'/proc/{pid}/cmdline') else ''
        if 'uvicorn' in proc_cmd or '8000' in proc_cmd or 'backend.main' in proc_cmd:
            os.kill(pid, signal.SIGKILL)
            print(f'Killed PID {pid} ({proc_cmd[:60]})')
    except:
        pass

time.sleep(2)
print('Done. Port 8000 should be free.')
