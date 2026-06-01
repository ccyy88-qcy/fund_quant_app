"""市场数据API路由"""
from fastapi import APIRouter
from typing import Optional

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from quant_engine import data_fetcher as df

router = APIRouter(prefix='/api/market', tags=['market'])


@router.get('/index')
async def market_index():
    """主要指数行情"""
    data = df.get_market_index()
    return {'data': data}


@router.get('/sectors')
async def sector_performance():
    """申万行业涨跌排行"""
    data = df.get_sector_performance()
    return {'data': data}


@router.get('/overview')
async def market_overview():
    """市场概览（指数+行业+热门）"""
    indices = df.get_market_index()
    sectors = df.get_sector_performance()[:10]
    return {'data': {'indices': indices, 'sectors': sectors}}
