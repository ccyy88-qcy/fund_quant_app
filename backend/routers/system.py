"""系统管理 API路由 — 后端状态/启停控制"""
from fastapi import APIRouter
import os
import sys
import subprocess
import signal
from datetime import datetime

router = APIRouter(prefix='/api/system', tags=['system'])

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START_SCRIPT = os.path.join(os.path.dirname(BACKEND_DIR), 'start_backend.sh')


@router.get('/status')
async def system_status():
    """系统状态 — 服务运行状态 + 进程信息"""
    pid = os.getpid()
    uptime_seconds = None
    try:
        import time
        uptime_seconds = int(time.time() - os.path.getctime('/proc/self/stat'))
    except:
        pass

    # 检查start_backend.sh是否存在
    has_start_script = os.path.exists(START_SCRIPT)

    # Python版本
    py_version = f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'

    return {
        'data': {
            'status': 'running',
            'pid': pid,
            'uptime_seconds': uptime_seconds,
            'python_version': py_version,
            'backend_dir': BACKEND_DIR,
            'has_start_script': has_start_script,
            'start_script_path': START_SCRIPT if has_start_script else None,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
    }


@router.post('/restart')
async def restart_backend():
    """重启后端服务"""
    try:
        # 启动新进程
        script = START_SCRIPT if os.path.exists(START_SCRIPT) else os.path.join(BACKEND_DIR, 'main.py')
        subprocess.Popen(
            ['bash', script] if script.endswith('.sh') else [sys.executable, script],
            cwd=BACKEND_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {'data': {'status': 'restarting', 'script': script}}
    except Exception as e:
        return {'error': str(e)}
