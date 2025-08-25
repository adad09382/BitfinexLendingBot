#!/bin/bash
# SimpleLendingBot 本地部署腳本

set -e

echo "🚀 SimpleLendingBot 部署腳本"
echo "=============================="

# 檢查 AWS CLI 配置
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI 未配置或憑證過期"
    exit 1
fi

echo "✅ AWS 憑證驗證通過"

# 獲取 ECR 登入
echo "🔐 登入 Amazon ECR..."
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 066691735887.dkr.ecr.us-west-2.amazonaws.com

# 構建 Docker 映像
echo "🏗️  構建 Docker 映像..."
docker build -f Dockerfile.aws --platform linux/amd64 -t simple-lending-bot:local .

# 標記映像
echo "🏷️  標記映像..."
docker tag simple-lending-bot:local 066691735887.dkr.ecr.us-west-2.amazonaws.com/simple-lending-bot:latest

# 推送映像
echo "📤 推送映像到 ECR..."
docker push 066691735887.dkr.ecr.us-west-2.amazonaws.com/simple-lending-bot:latest

# 強制重新部署 ECS 服務
echo "🔄 重新部署 ECS 服務..."
aws ecs update-service \
    --cluster simple-lending-bot-cluster \
    --service simple-lending-bot-service \
    --force-new-deployment \
    --region us-west-2 \
    > /dev/null

echo "⏳ 等待部署完成..."
aws ecs wait services-stable \
    --cluster simple-lending-bot-cluster \
    --services simple-lending-bot-service \
    --region us-west-2

# 顯示部署狀態
echo "📊 部署狀態:"
aws ecs describe-services \
    --cluster simple-lending-bot-cluster \
    --services simple-lending-bot-service \
    --query "services[0].{Status:status,Running:runningCount,Desired:desiredCount}" \
    --output table

echo ""
echo "🎉 部署完成！"
echo "💡 使用 'python monitor.py' 查看運行狀態"
echo "💡 使用 'python monitor.py watch' 開啟實時監控"