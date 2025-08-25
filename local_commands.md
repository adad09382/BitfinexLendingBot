# SimpleLendingBot 本地檢查指令

## 🔍 基本檢查指令

### 查看完整配置
```bash
source venv/bin/activate && python show_config.py
```
顯示所有 AWS 基礎設施、API 配置、Bot 參數等完整資訊

### 查看即時運行狀態  
```bash
source venv/bin/activate && python monitor.py
```
顯示 ECS 服務狀態、資料庫狀態、最近日誌

### 即時監控（每30秒刷新）
```bash
source venv/bin/activate && python monitor.py watch
```
持續監控 Bot 運行狀態，按 Ctrl+C 停止

### 健康檢查
```bash
source venv/bin/activate && python health_check.py
```
全面檢查所有組件是否正常運行

## 🚀 部署和管理指令

### 快速重新部署
```bash
./deploy.sh
```
重新構建 Docker 映像並部署到 AWS

### 手動環境變數設置
```bash
source venv/bin/activate && python update_env.py list
source venv/bin/activate && python update_env.py set BITFINEX_API_KEY "your-key"
```

## 🔧 AWS CLI 直接操作

### 檢查 ECS 服務狀態
```bash
aws ecs describe-services --cluster simple-lending-bot-cluster --services simple-lending-bot-service --query "services[0].{Status:status,Running:runningCount,Desired:desiredCount}" --output table
```

### 檢查最新 Task Definition
```bash
aws ecs describe-task-definition --task-definition simple-lending-bot --query "taskDefinition.{Revision:revision,CPU:cpu,Memory:memory}" --output table
```

### 檢查 RDS 狀態
```bash
aws rds describe-db-instances --db-instance-identifier simple-lending-bot-db --query "DBInstances[0].{Status:DBInstanceStatus,Engine:Engine,Class:DBInstanceClass}" --output table
```

### 查看 SSM 參數
```bash
aws ssm describe-parameters --filters "Name=Name,Values=/simple-lending-bot/" --query "Parameters[*].{Name:Name,Type:Type}" --output table
```

### 強制重新部署 ECS 服務
```bash
aws ecs update-service --cluster simple-lending-bot-cluster --service simple-lending-bot-service --force-new-deployment
```

### 查看最近日誌
```bash
aws logs describe-log-streams --log-group-name "/ecs/simple-lending-bot" --order-by LastEventTime --descending --max-items 1 --query "logStreams[0].logStreamName" --output text

# 然後用上面獲得的 stream name
aws logs get-log-events --log-group-name "/ecs/simple-lending-bot" --log-stream-name "ecs/simple-lending-bot/YOUR-TASK-ID" --limit 20
```

## 🛠️ 故障排除指令

### 檢查 Docker 是否運行
```bash
docker info
```

### 測試 AWS CLI 連接
```bash
aws sts get-caller-identity
```

### 檢查本地環境變數
```bash
source venv/bin/activate && python -c "from decouple import config; print('API Key:', 'Set' if config('BITFINEX_API_KEY', default='') else 'Not Set')"
```

### 查看所有運行中的 Tasks
```bash
aws ecs list-tasks --cluster simple-lending-bot-cluster --output table
```

### 檢查特定 Task 的詳細資訊
```bash
aws ecs describe-tasks --cluster simple-lending-bot-cluster --tasks TASK-ARN --query "tasks[0].{Status:lastStatus,Health:healthStatus,CreatedAt:createdAt}"
```

## 📊 監控指令

### 查看服務事件
```bash
aws ecs describe-services --cluster simple-lending-bot-cluster --services simple-lending-bot-service --query "services[0].events[:5]" --output table
```

### 檢查 ECR 映像
```bash
aws ecr describe-images --repository-name simple-lending-bot --query "imageDetails[*].{Tags:imageTags,Size:imageSizeInBytes,PushedAt:imagePushedAt}" --output table
```

## 🎯 常用組合指令

### 完整狀態檢查（推薦）
```bash
echo "=== 完整狀態檢查 ===" && \
source venv/bin/activate && python health_check.py && \
echo -e "\n=== 最新日誌 ===" && \
source venv/bin/activate && python monitor.py
```

### 重新部署並監控
```bash
./deploy.sh && echo "等待部署..." && sleep 60 && source venv/bin/activate && python monitor.py
```

## 💡 提示

- 所有 Python 指令都需要先 `source venv/bin/activate`
- AWS CLI 指令需要正確的 AWS 憑證配置
- `monitor.py watch` 可以即時監控，按 Ctrl+C 退出
- `health_check.py` 會返回錯誤代碼，可用於自動化腳本