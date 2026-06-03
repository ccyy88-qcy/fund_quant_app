#!/data/data/com.termux/files/usr/bin/bash
# 基金量化API 看门狗 — 每5分钟检查，挂了自动重启

BACKEND_DIR="/data/data/com.termux/files/home/fund_quant_app/backend"
LOG_FILE="/data/data/com.termux/files/home/fund_quant_app/watchdog.log"
HEALTH_URL="http://127.0.0.1:8000/api/health"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

# 健康检查（3秒超时）
result=$(curl -s --connect-timeout 3 --max-time 5 "$HEALTH_URL" 2>&1)
if echo "$result" | grep -q '"status":"ok"'; then
  # 服务正常，无事发生
  exit 0
fi

# 服务挂了 — 重启
log "健康检查失败: $result" 
log "开始重启..."

# 杀老进程
pids=$(pgrep -f "python3.*main.py" 2>/dev/null)
if [ -n "$pids" ]; then
  log "杀掉旧进程: $pids"
  kill -9 $pids 2>/dev/null
  sleep 2
fi

# 启动新进程
cd "$BACKEND_DIR" || { log "目录不存在: $BACKEND_DIR"; exit 1; }
nohup python3 main.py > /dev/null 2>&1 &
new_pid=$!
log "新进程已启动 PID=$new_pid"

# 等几秒确认启动成功
sleep 4
check=$(curl -s --connect-timeout 3 --max-time 5 "$HEALTH_URL" 2>&1)
if echo "$check" | grep -q '"status":"ok"'; then
  log "重启成功 ✓"
else
  log "重启后健康检查仍然失败: $check"
fi
