"""基金全能量化工具 — FastAPI后端"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os, sys

# 确保能找到quant_engine
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from routers import funds, market, factors, rotation, portfolio, strategy, risk, analysis, dca, sentiment, system, holding, scanner

app = FastAPI(title='基金全量量化工具', version='1.0.0')

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


@app.get('/api/health')
async def health():
    """健康检查"""
    return {'status': 'ok', 'version': '1.0.0'}


def main():
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '8000'))
    print(f'🚀 基金量化API服务启动: http://{host}:{port}')
    print(f'📖 Docs: http://{host}:{port}/docs')
    uvicorn.run(app, host=host, port=port, log_level='info')


if __name__ == '__main__':
    main()
