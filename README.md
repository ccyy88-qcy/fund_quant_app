# 基金全量化工具 🚀

Flutter App + Python FastAPI 后端，一站式基金量化分析工具。

## 架构

```
fund_quant_app/
├── backend/           # Python FastAPI 后端
│   ├── main.py       # API入口
│   ├── quant_engine/ # 量化引擎
│   │   ├── data_fetcher.py     # 数据获取 (akshare/东方财富)
│   │   ├── indicators.py       # 技术指标 (MA/RSI/MACD/布林带/CCI/ADX)
│   │   ├── signals.py          # MA10+MA60 规则信号 + 估值豁免
│   │   ├── risk_metrics.py     # 年化收益/夏普/回撤/胜率/盈亏比
│   │   └── candlestick_patterns.py  # 15种K线形态识别
│   └── routers/      # API路由
│       ├── funds.py  # 基金搜索/信息/K线/信号/回测/自选
│       └── market.py # 指数/行业/市场概览
├── flutter_app/      # Flutter移动端
│   └── lib/
│       ├── main.dart          # 入口+底部导航
│       ├── theme/             # 霓虹紫蓝深色主题
│       ├── pages/             # 页面
│       │   ├── dashboard_page.dart  # 仪表盘(指数/自选/市场雷达)
│       │   ├── quant_page.dart      # 量化回测(搜索/信号/回测绩效)
│       │   ├── kline_page.dart      # K线分析(蜡烛图/均线/RSI/CCI)
│       │   └── settings_page.dart   # 设置(服务器地址)
│       └── services/          # API调用
└── start_backend.sh  # 后端启动脚本
```

## 后端启动

```bash
cd ~/fund_quant_app
bash start_backend.sh
```

默认监听 `http://0.0.0.0:8000`

## Flutter编译

GitHub Actions 自动构建（push到main分支触发），或本地：

```bash
cd flutter_app
flutter build apk --release --target-platform android-arm64
```

## API文档

启动后端后访问 `http://{ip}:8000/docs`

## 功能

- 📊 大盘指数实时行情
- 💰 自选基金实时估值
- 🔍 基金搜索/信息查询
- 📈 K线图 + MA10/MA60 + RSI + CCI + MACD + 布林带
- 🎯 MA10+MA60量化信号（含PE/PB估值豁免规则）
- 📉 历史回测（胜率/盈亏比/最大回撤/总收益）
- 🔮 K线形态识别（15种经典形态）
- 🏭 申万行业涨跌排行
