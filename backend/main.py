"""基金全能量化工具 — FastAPI后端（带看门狗自动重启）"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os, sys, time, threading, logging

# numpy序列化支持
import numpy as np
import json

logger = logging.getLogger('watchdog')

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, (np.ndarray,)): return obj.tolist()
        if isinstance(obj, (np.bool_,)): return bool(obj)
        return super().default(obj)

from fastapi.responses import JSONResponse as FastJSONResponse
class NumpyJSONResponse(FastJSONResponse):
    def render(self, content: dict) -> bytes:
        return json.dumps(content, cls=NumpyEncoder, ensure_ascii=False).encode('utf-8')

# 确保能找到quant_engine
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from routers import funds, market, factors, rotation, portfolio, strategy, risk, analysis, dca, sentiment, system, holding, scanner, stock_monitor

app = FastAPI(title='基金全量量化工具', version='1.0.0', default_response_class=NumpyJSONResponse)

# CORS — 允许Flutter App跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(funds.router)
app.include_router(market.router)
app.include_router(factors.router)
app.include_router(rotation.router)
app.include_router(portfolio.router)
app.include_router(strategy.router)
app.include_router(risk.router)
app.include_router(analysis.router)
app.include_router(dca.router)
app.include_router(sentiment.router)
app.include_router(system.router)
app.include_router(holding.router)
app.include_router(scanner.router)
app.include_router(stock_monitor.router)


@app.get('/api/health')
async def health():
    """健康检查"""
    return {'status': 'ok', 'version': '1.0.0'}


def _start_watchdog(host: str, port: int):
    """看门狗线程：每60秒检查一次健康，连续3次失败则自杀重启"""
    import urllib.request
    url = f'http://{host}:{port}/api/health'
    failures = 0
    max_failures = 3

    while True:
        time.sleep(60)
        try:
            resp = urllib.request.urlopen(url, timeout=10)
            if resp.status == 200:
                failures = 0  # 恢复计数
                continue
        except Exception:
            failures += 1
            logger.warning(f'看门狗：健康检查失败 {failures}/{max_failures}')

        if failures >= max_failures:
            logger.error('看门狗：服务已死，触发自杀重启')
            # 强制退出，外部包装脚本会重新拉起
            os._exit(1)


def _run_with_restart(host: str, port: int):
    """带重启循环的运行，看门狗退出后自动重启"""
    while True:
        print(f'🚀 基金量化API服务启动: http://{host}:{port}')
        print(f'📖 Docs: http://{host}:{port}/docs')

        # 启动看门狗
        watchdog = threading.Thread(target=_start_watchdog, args=(host, port), daemon=True)
        watchdog.start()

        try:
            uvicorn.run(app, host=host, port=port, log_level='info')
        except SystemExit:
            pass
        except Exception as e:
            print(f'💥 服务异常退出: {e}')

        print('🔄 5秒后重启...')
        time.sleep(5)


def main():
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '8000'))
    _run_with_restart(host, port)


if __name__ == '__main__':
    main()
