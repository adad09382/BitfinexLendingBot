#!/bin/bash
# BitfinexLendingBot 生產部署腳本
# 自動化部署和健康檢查流程

set -e

echo "🚀 BitfinexLendingBot 生產部署開始..."

# 檢查必需的環境文件
if [ ! -f ".env" ]; then
    echo "❌ 錯誤：.env 文件不存在"
    echo "請複製 .env.example 為 .env 並配置必要的環境變量"
    exit 1
fi

# 檢查 Docker 和 Docker Compose
if ! command -v docker &> /dev/null; then
    echo "❌ 錯誤：Docker 未安裝"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ 錯誤：Docker Compose 未安裝"
    exit 1
fi

# 創建必需的目錄
echo "📁 創建必需的目錄..."
mkdir -p logs backups config nginx/ssl

# 設置權限
chmod +x scripts/*.sh
chmod +x scripts/*.py

# 檢查並初始化數據庫
echo "🗄️ 初始化數據庫..."
if [ -f "scripts/create_monitoring_tables.sql" ]; then
    echo "監控表腳本已就緒"
fi

# 構建和啟動服務
echo "🔨 構建 Docker 映像..."
docker-compose build --no-cache

echo "🚀 啟動核心服務..."
docker-compose up -d postgres redis bitfinex-bot

# 等待服務健康檢查
echo "⏳ 等待服務健康檢查 (最多 120 秒)..."
timeout=120
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if docker-compose ps | grep -q "Up (healthy)"; then
        echo "✅ 核心服務健康檢查通過"
        break
    fi
    sleep 5
    elapsed=$((elapsed + 5))
    echo "等待中... ($elapsed/$timeout 秒)"
done

if [ $elapsed -ge $timeout ]; then
    echo "❌ 服務健康檢查超時"
    echo "查看日誌："
    docker-compose logs --tail=50 bitfinex-bot
    exit 1
fi

# 執行數據庫初始化（如果需要）
echo "🗄️ 執行數據庫初始化..."
docker-compose exec postgres psql -U bitfinex_user -d bitfinex_bot -f /docker-entrypoint-initdb.d/01-monitoring.sql 2>/dev/null || echo "監控表可能已存在"

# 可選：啟動監控服務
read -p "是否啟動監控服務？[y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📊 啟動監控服務..."
    docker-compose --profile monitoring up -d monitor
fi

# 可選：啟動 Web 介面
read -p "是否啟動 Web 介面 (Nginx)？[y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🌐 啟動 Web 介面..."
    docker-compose --profile web up -d nginx
fi

# 顯示運行狀態
echo "📊 服務運行狀態："
docker-compose ps

# 顯示日誌
echo "📝 最近的日誌："
docker-compose logs --tail=20 bitfinex-bot

echo ""
echo "✅ 部署完成！"
echo ""
echo "📋 管理命令："
echo "  查看狀態: docker-compose ps"
echo "  查看日誌: docker-compose logs -f bitfinex-bot"
echo "  停止服務: docker-compose down"
echo "  更新服務: ./scripts/update.sh"
echo ""
echo "📁 重要目錄："
echo "  日誌文件: ./logs/"
echo "  數據備份: ./backups/"
echo "  配置文件: ./config/"
echo ""
echo "🚨 監控："
if docker-compose ps | grep -q "monitor.*Up"; then
    echo "  監控服務: ✅ 運行中"
    echo "  告警配置: 檢查 Telegram 通知"
else
    echo "  監控服務: ⚠️ 未啟動"
    echo "  啟動監控: docker-compose --profile monitoring up -d monitor"
fi

# 創建 systemd 服務文件的提示
echo ""
echo "💡 建議："
echo "  1. 設置自動備份: crontab -e"
echo "     添加: 0 2 * * * /path/to/scripts/backup_db.sh"
echo "  2. 設置系統服務: 查看 DEPLOYMENT.md 中的 systemd 配置"
echo "  3. 配置防火牆: 只開放必需的端口"
echo ""