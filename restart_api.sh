#!/data/data/com.termux/files/usr/bin/bash
# 杀旧进程
for pid in $(pgrep -f "uvicorn"); do
  kill $pid 2>/dev/null
done
sleep 2
# 清缓存
rm -f /data/data/com.termux/files/home/fund_quant_app/backend/data/*.json
# 重启
cd /data/data/com.termux/files/home/fund_quant_app
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
