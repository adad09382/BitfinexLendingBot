# SimpleLendingBot AWS 操作指令大全

## 📋 目錄
- [環境變數管理](#環境變數管理)
- [ECS 容器服務管理](#ecs-容器服務管理)
- [RDS 資料庫管理](#rds-資料庫管理)
- [ECR 映像倉庫管理](#ecr-映像倉庫管理)
- [CloudWatch 日誌管理](#cloudwatch-日誌管理)
- [IAM 權限管理](#iam-權限管理)
- [完整部署和監控](#完整部署和監控)
- [故障排除](#故障排除)

---

## 🔐 環境變數管理

### SSM Parameter Store 操作

#### 查看所有環境變數
```bash
source venv/bin/activate && python update_env.py list
```

#### 設置環境變數
```bash
# 設置 API 密鑰
source venv/bin/activate && python update_env.py set BITFINEX_API_KEY "你的API密鑰"
source venv/bin/activate && python update_env.py set BITFINEX_API_SECRET "你的API秘密"

# 設置交易參數
source venv/bin/activate && python update_env.py set MIN_ORDER_AMOUNT "200"
source venv/bin/activate && python update_env.py set MAX_LOAN_AMOUNT "50000"
source venv/bin/activate && python update_env.py set TARGET_ANNUAL_RATE "0.15"
```

#### 使用 AWS CLI 直接操作 SSM
```bash
# 查看所有參數
aws ssm describe-parameters --filters "Key=Name,Values=/simple-lending-bot/" --query "Parameters[*].{Name:Name,Type:Type}" --output table

# 直接設置參數
aws ssm put-parameter --name "/simple-lending-bot/MIN_ORDER_AMOUNT" --value "200" --type "String" --overwrite

# 獲取參數值（加密參數需要 --with-decryption）
aws ssm get-parameter --name "/simple-lending-bot/BITFINEX_API_KEY" --with-decryption --query "Parameter.Value" --output text

# 刪除參數
aws ssm delete-parameter --name "/simple-lending-bot/參數名"
```

#### 更新 Task Definition 並部署
```bash
source venv/bin/activate && python update_env.py update-task-def
```

---

## 🚀 ECS 容器服務管理

### 集群管理
```bash
# 查看所有集群
aws ecs list-clusters --query "clusterArns" --output table

# 查看集群詳細資訊
aws ecs describe-clusters --clusters simple-lending-bot-cluster --include STATISTICS --output table

# 創建新集群
aws ecs create-cluster --cluster-name simple-lending-bot-cluster
```

### 服務管理
```bash
# 查看服務狀態
aws ecs describe-services --cluster simple-lending-bot-cluster --services simple-lending-bot-service --query "services[0].{Status:status,Running:runningCount,Desired:desiredCount,Deployment:deployments[0].rolloutState}" --output table

# 強制重新部署
aws ecs update-service --cluster simple-lending-bot-cluster --service simple-lending-bot-service --force-new-deployment

# 更新服務設定
aws ecs update-service --cluster simple-lending-bot-cluster --service simple-lending-bot-service --task-definition simple-lending-bot:最新版本號

# 停止服務
aws ecs update-service --cluster simple-lending-bot-cluster --service simple-lending-bot-service --desired-count 0

# 啟動服務
aws ecs update-service --cluster simple-lending-bot-cluster --service simple-lending-bot-service --desired-count 1
```

### Task 管理
```bash
# 查看運行中的 Tasks
aws ecs list-tasks --cluster simple-lending-bot-cluster --service-name simple-lending-bot-service --output table

# 查看 Task 詳細資訊
aws ecs describe-tasks --cluster simple-lending-bot-cluster --tasks TASK-ARN --query "tasks[0].{Status:lastStatus,Health:healthStatus,CreatedAt:createdAt,TaskDefArn:taskDefinitionArn}" --output table

# 停止特定 Task
aws ecs stop-task --cluster simple-lending-bot-cluster --task TASK-ARN --reason "手動停止"
```

### Task Definition 管理
```bash
# 查看當前 Task Definition
aws ecs describe-task-definition --task-definition simple-lending-bot --query "taskDefinition.{Revision:revision,CPU:cpu,Memory:memory,Image:containerDefinitions[0].image}" --output table

# 查看所有版本
aws ecs list-task-definitions --family-prefix simple-lending-bot --query "taskDefinitionArns" --output table

# 查看環境變數配置
aws ecs describe-task-definition --task-definition simple-lending-bot --query "taskDefinition.containerDefinitions[0].{Environment:environment,Secrets:secrets}" --output json
```

---

## 💾 RDS 資料庫管理

### 資料庫狀態查看
```bash
# 查看資料庫狀態
aws rds describe-db-instances --db-instance-identifier simple-lending-bot-db --query "DBInstances[0].{Status:DBInstanceStatus,Engine:Engine,Class:DBInstanceClass,Storage:AllocatedStorage,Endpoint:Endpoint.Address}" --output table

# 查看所有 RDS 實例
aws rds describe-db-instances --query "DBInstances[*].{Name:DBInstanceIdentifier,Engine:Engine,Status:DBInstanceStatus}" --output table
```

### 資料庫操作
```bash
# 重啟資料庫
aws rds reboot-db-instance --db-instance-identifier simple-lending-bot-db

# 停止資料庫（節省成本）
aws rds stop-db-instance --db-instance-identifier simple-lending-bot-db

# 啟動資料庫
aws rds start-db-instance --db-instance-identifier simple-lending-bot-db

# 修改資料庫參數
aws rds modify-db-instance --db-instance-identifier simple-lending-bot-db --allocated-storage 30 --apply-immediately
```

---

## 📦 ECR 映像倉庫管理

### 映像管理
```bash
# 查看映像列表
aws ecr describe-images --repository-name simple-lending-bot --query "imageDetails[*].{Tags:imageTags,Size:imageSizeInBytes,PushedAt:imagePushedAt}" --output table

# 登入 ECR
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 066691735887.dkr.ecr.us-west-2.amazonaws.com

# 構建並推送映像
docker build -f Dockerfile.aws --platform linux/amd64 -t simple-lending-bot:local .
docker tag simple-lending-bot:local 066691735887.dkr.ecr.us-west-2.amazonaws.com/simple-lending-bot:latest
docker push 066691735887.dkr.ecr.us-west-2.amazonaws.com/simple-lending-bot:latest

# 刪除舊映像（節省空間）
aws ecr batch-delete-image --repository-name simple-lending-bot --image-ids imageTag=舊標籤
```

---

## 📊 CloudWatch 日誌管理

### 日誌查看
```bash
# 查看 Log Groups
aws logs describe-log-groups --log-group-name-prefix "/ecs/" --query "logGroups[*].logGroupName" --output table

# 查看最新的 Log Stream
aws logs describe-log-streams --log-group-name "/ecs/simple-lending-bot" --order-by LastEventTime --descending --max-items 1 --query "logStreams[0].logStreamName" --output text

# 查看最近日誌（需要先獲取 stream name）
STREAM_NAME=$(aws logs describe-log-streams --log-group-name "/ecs/simple-lending-bot" --order-by LastEventTime --descending --max-items 1 --query "logStreams[0].logStreamName" --output text)
aws logs get-log-events --log-group-name "/ecs/simple-lending-bot" --log-stream-name "$STREAM_NAME" --limit 50 --query "events[*].message" --output table

# 實時追蹤日誌（需要安裝 aws-cli v2）
aws logs tail "/ecs/simple-lending-bot" --follow
```

---

## 🔑 IAM 權限管理

### 角色管理
```bash
# 查看角色
aws iam get-role --role-name ecsTaskExecutionRole --query "Role.{Arn:Arn,CreateDate:CreateDate}" --output table
aws iam get-role --role-name ecsTaskRole --query "Role.{Arn:Arn,CreateDate:CreateDate}" --output table

# 查看角色的策略
aws iam list-attached-role-policies --role-name ecsTaskExecutionRole --output table
aws iam list-attached-role-policies --role-name ecsTaskRole --output table

# 添加策略到角色
aws iam attach-role-policy --role-name ecsTaskRole --policy-arn arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess
```

### 使用者管理
```bash
# 查看當前使用者
aws sts get-caller-identity --query "{UserId:UserId,Account:Account,Arn:Arn}" --output table

# 查看使用者權限
aws iam list-attached-user-policies --user-name simple-lending-bot-deploy --output table
```

---

## 📈 完整部署和監控

### 一鍵部署腳本
```bash
# 使用預建的部署腳本
./deploy.sh

# 或者手動步驟
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 066691735887.dkr.ecr.us-west-2.amazonaws.com
docker build -f Dockerfile.aws --platform linux/amd64 -t simple-lending-bot:local .
docker tag simple-lending-bot:local 066691735887.dkr.ecr.us-west-2.amazonaws.com/simple-lending-bot:latest
docker push 066691735887.dkr.ecr.us-west-2.amazonaws.com/simple-lending-bot:latest
aws ecs update-service --cluster simple-lending-bot-cluster --service simple-lending-bot-service --force-new-deployment
```

### 監控腳本
```bash
# 查看完整配置
source venv/bin/activate && python show_config.py

# 即時監控
source venv/bin/activate && python monitor.py

# 持續監控
source venv/bin/activate && python monitor.py watch

# 健康檢查
source venv/bin/activate && python health_check.py
```

### 等待部署完成
```bash
# 等待服務穩定
aws ecs wait services-stable --cluster simple-lending-bot-cluster --services simple-lending-bot-service --region us-west-2

# 檢查部署狀態
aws ecs describe-services --cluster simple-lending-bot-cluster --services simple-lending-bot-service --query "services[0].deployments[*].{Status:rolloutState,CreatedAt:createdAt}" --output table
```

---

## 🔧 故障排除

### 服務無法啟動
```bash
# 查看服務事件
aws ecs describe-services --cluster simple-lending-bot-cluster --services simple-lending-bot-service --query "services[0].events[:10]" --output table

# 查看 Task 停止原因
aws ecs describe-tasks --cluster simple-lending-bot-cluster --tasks $(aws ecs list-tasks --cluster simple-lending-bot-cluster --service-name simple-lending-bot-service --desired-status STOPPED --query "taskArns[0]" --output text) --query "tasks[0].{StopCode:stopCode,StopReason:stoppedReason}" --output table
```

### 環境變數問題
```bash
# 檢查 Task Definition 中的環境變數
aws ecs describe-task-definition --task-definition simple-lending-bot --query "taskDefinition.containerDefinitions[0].{Environment:environment,Secrets:secrets}" --output json

# 測試 SSM 參數讀取
aws ssm get-parameter --name "/simple-lending-bot/BITFINEX_API_KEY" --with-decryption --query "Parameter.Value" --output text

# 檢查 IAM 權限
aws iam simulate-principal-policy --policy-source-arn arn:aws:iam::066691735887:role/ecsTaskRole --action-names ssm:GetParameter --resource-arns "arn:aws:ssm:us-west-2:066691735887:parameter/simple-lending-bot/*" --query "EvaluationResults[*].{Action:EvalActionName,Decision:EvalDecision}" --output table
```

### 網路連接問題
```bash
# 查看安全群組
aws ec2 describe-security-groups --group-ids sg-05574ccdd10d47997 --query "SecurityGroups[0].{GroupId:GroupId,InboundRules:IpPermissions}" --output table

# 查看子網路
aws ec2 describe-subnets --subnet-ids subnet-0dce450843cda23e0 subnet-0f3d9535fc692346a --query "Subnets[*].{SubnetId:SubnetId,AvailabilityZone:AvailabilityZone,State:State}" --output table
```

---

## 🌐 AWS Console 快速連結

```bash
echo "📱 AWS Console 直接連結:"
echo "ECS 集群: https://us-west-2.console.aws.amazon.com/ecs/v2/clusters/simple-lending-bot-cluster"
echo "RDS 資料庫: https://us-west-2.console.aws.amazon.com/rds/home?region=us-west-2#database:id=simple-lending-bot-db"
echo "SSM 參數: https://us-west-2.console.aws.amazon.com/systems-manager/parameters/?region=us-west-2&tab=Table"
echo "CloudWatch 日誌: https://us-west-2.console.aws.amazon.com/cloudwatch/home?region=us-west-2#logsV2:log-groups/log-group/%2Fecs%2Fsimple-lending-bot"
echo "ECR 倉庫: https://us-west-2.console.aws.amazon.com/ecr/repositories/simple-lending-bot?region=us-west-2"
```

---

## 💰 成本監控

```bash
# 查看當前月份的成本（需要 Cost Explorer 權限）
aws ce get-cost-and-usage --time-period Start=2025-08-01,End=2025-08-31 --granularity MONTHLY --metrics BlendedCost --group-by Type=DIMENSION,Key=SERVICE --output table

# 查看免費方案使用量（需要 Budgets 權限）
aws budgets describe-budget --account-id 066691735887 --budget-name "My Zero Spend Budget"
```

---

## 🔄 自動化腳本

### 每日健康檢查腳本
```bash
#!/bin/bash
echo "🔍 每日健康檢查 - $(date)"
source venv/bin/activate && python health_check.py
if [ $? -eq 0 ]; then
    echo "✅ 系統健康"
else
    echo "⚠️ 發現問題，請檢查"
    source venv/bin/activate && python monitor.py
fi
```

### 緊急重啟腳本
```bash
#!/bin/bash
echo "🚨 緊急重啟 Bot"
aws ecs update-service --cluster simple-lending-bot-cluster --service simple-lending-bot-service --force-new-deployment
aws ecs wait services-stable --cluster simple-lending-bot-cluster --services simple-lending-bot-service
echo "✅ 重啟完成"
source venv/bin/activate && python monitor.py
```

---

## 📝 注意事項

1. **區域設定**: 所有資源都在 `us-west-2` 區域
2. **免費方案**: 確保使用量在免費額度內
3. **安全性**: API 密鑰使用 SecureString 類型存儲
4. **備份**: 定期備份 SSM 參數設定
5. **監控**: 建議設置 CloudWatch 警報監控異常

---

*最後更新: 2025-08-25*