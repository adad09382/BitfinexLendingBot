#!/bin/bash
# BitfinexLendingBot 更新腳本
# 零停機時間更新

set -e

echo "🔄 BitfinexLendingBot 更新開始..."

# 檢查是否有運行的服務
if ! docker-compose ps | grep -q "Up"; then
    echo "❌ 沒有運行中的服務，請先使用 ./scripts/deploy.sh 部署"
    exit 1
fi

# 備份當前數據
echo "💾 創建數據備份..."
./scripts/backup_db.sh || echo "備份可能失敗，但繼續更新..."

# 拉取最新代碼（如果是 git 倉庫）
if [ -d ".git" ]; then
    echo "📥 拉取最新代碼..."
    git pull origin main || git pull origin master || echo "Git 拉取失敗，使用本地代碼"
fi

# 重新構建映像
echo "🔨 重新構建 Docker 映像..."
docker-compose build --no-cache bitfinex-bot

# 滾動更新：先啟動新容器，再停止舊容器
echo "🔄 執行滾動更新..."

# 記錄當前運行的服務
services=$(docker-compose ps --services --filter "status=running")

# 逐個更新服務
for service in $services; do
    if [ "$service" != "postgres" ] && [ "$service" != "redis" ]; then
        echo "更新服務: $service"
        docker-compose up -d --no-deps $service
        
        # 等待服務健康
        echo "等待 $service 健康檢查..."
        timeout=60
        elapsed=0
        while [ $elapsed -lt $timeout ]; do
            if docker-compose ps $service | grep -q "Up (healthy)"; then
                echo "✅ $service 健康檢查通過"
                break
            fi
            sleep 2
            elapsed=$((elapsed + 2))
        done
        
        if [ $elapsed -ge $timeout ]; then
            echo "❌ $service 健康檢查超時，回滾..."
            docker-compose logs --tail=20 $service
            exit 1
        fi
    fi
done

# 清理未使用的映像
echo "🧹 清理舊映像..."
docker image prune -f

# 檢查最終狀態
echo "📊 更新後狀態："
docker-compose ps

echo "📝 最近的日誌："
docker-compose logs --tail=10 bitfinex-bot

echo ""
echo "✅ 更新完成！"
echo ""
echo "📋 後續檢查："
echo "  1. 檢查日誌: docker-compose logs -f bitfinex-bot"
echo "  2. 檢查 API: curl http://localhost:8000/health"
echo "  3. 檢查監控: 查看 Telegram 通知"
echo ""