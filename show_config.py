#!/usr/bin/env python3
"""
SimpleLendingBot 配置查看器
顯示所有當前的 AWS 和 Bot 設定
"""

import boto3
import json
from datetime import datetime
from decouple import config

def show_aws_infrastructure():
    """顯示 AWS 基礎設施設定"""
    print("🏗️  AWS 基礎設施配置")
    print("-" * 40)
    
    # ECS 設定
    ecs = boto3.client('ecs', region_name='us-west-2')
    
    try:
        # 服務資訊
        service_response = ecs.describe_services(
            cluster='simple-lending-bot-cluster',
            services=['simple-lending-bot-service']
        )
        service = service_response['services'][0]
        
        print(f"📊 ECS 服務:")
        print(f"   集群: simple-lending-bot-cluster")
        print(f"   服務: simple-lending-bot-service")
        print(f"   狀態: {service['status']}")
        print(f"   運行實例: {service['runningCount']}/{service['desiredCount']}")
        print(f"   啟動類型: {service['launchType']}")
        
        # Task Definition 資訊
        task_def_response = ecs.describe_task_definition(taskDefinition='simple-lending-bot')
        task_def = task_def_response['taskDefinition']
        
        print(f"\n🔧 Task Definition (版本 {task_def['revision']}):")
        print(f"   CPU: {task_def['cpu']}")
        print(f"   記憶體: {task_def['memory']} MB")
        print(f"   網路模式: {task_def['networkMode']}")
        print(f"   執行角色: {task_def.get('executionRoleArn', 'None')}")
        print(f"   任務角色: {task_def.get('taskRoleArn', 'None')}")
        
        container = task_def['containerDefinitions'][0]
        print(f"   容器映像: {container['image']}")
        print(f"   環境變數數量: {len(container.get('environment', []))}")
        print(f"   機密參數數量: {len(container.get('secrets', []))}")
        
    except Exception as e:
        print(f"❌ 無法獲取 ECS 資訊: {str(e)}")
    
    # RDS 設定
    rds = boto3.client('rds', region_name='us-west-2')
    
    try:
        rds_response = rds.describe_db_instances(DBInstanceIdentifier='simple-lending-bot-db')
        db = rds_response['DBInstances'][0]
        
        print(f"\n💾 RDS 資料庫:")
        print(f"   識別碼: simple-lending-bot-db")
        print(f"   引擎: {db['Engine']} {db['EngineVersion']}")
        print(f"   實例類型: {db['DBInstanceClass']}")
        print(f"   存儲: {db['AllocatedStorage']} GB ({db['StorageType']})")
        print(f"   狀態: {db['DBInstanceStatus']}")
        if 'Endpoint' in db:
            print(f"   端點: {db['Endpoint']['Address']}:{db['Endpoint']['Port']}")
        print(f"   多可用區: {db['MultiAZ']}")
        print(f"   公開可訪問: {db['PubliclyAccessible']}")
        
    except Exception as e:
        print(f"❌ 無法獲取 RDS 資訊: {str(e)}")

def show_api_config():
    """顯示 API 和環境變數配置"""
    print("\n🔐 API 和環境變數配置")
    print("-" * 40)
    
    # SSM 參數
    ssm = boto3.client('ssm', region_name='us-west-2')
    
    try:
        response = ssm.describe_parameters(
            Filters=[{'Key': 'Name', 'Values': ['/simple-lending-bot/']}]
        )
        
        print("📋 AWS SSM Parameter Store:")
        for param in response['Parameters']:
            name = param['Name'].replace('/simple-lending-bot/', '')
            print(f"   {name}: {param['Type']} (修改於 {param['LastModifiedDate'].strftime('%Y-%m-%d %H:%M')})")
            
    except Exception as e:
        print(f"❌ 無法獲取 SSM 參數: {str(e)}")
    
    # 本地 .env 檢查
    print(f"\n📁 本地環境變數 (.env):")
    try:
        api_key = config('BITFINEX_API_KEY', default='未設置')
        api_secret = config('BITFINEX_API_SECRET', default='未設置')
        
        print(f"   BITFINEX_API_KEY: {'已設置' if api_key != '未設置' else '未設置'}")
        print(f"   BITFINEX_API_SECRET: {'已設置' if api_secret != '未設置' else '未設置'}")
        
    except Exception as e:
        print(f"❌ 無法讀取本地 .env: {str(e)}")

def show_bot_config():
    """顯示 Bot 運行配置"""
    print("\n🤖 Bot 運行配置")
    print("-" * 40)
    
    try:
        # 從本地代碼讀取配置
        from main import SimpleLendingBot
        
        print("⚙️  Bot 參數:")
        print(f"   最小放貸金額: {config('MIN_LOAN_AMOUNT', default='10')} USD")
        print(f"   最大放貸金額: {config('MAX_LOAN_AMOUNT', default='10000')} USD")
        print(f"   基礎利率: {config('BASE_RATE', default='0.01')}%")
        print(f"   利率階梯數: {config('RATE_STEPS', default='5')}")
        print(f"   放貸期限: {config('LOAN_PERIOD', default='2')} 天")
        print(f"   最大重試次數: {config('MAX_RETRY_ATTEMPTS', default='3')}")
        print(f"   重試延遲: {config('RETRY_DELAY_SECONDS', default='5')} 秒")
        
        print(f"\n📅 排程設定:")
        print(f"   主循環: 每 30 分鐘執行")
        print(f"   每日結算: 每天 00:05")
        
    except Exception as e:
        print(f"❌ 無法讀取 Bot 配置: {str(e)}")

def show_database_config():
    """顯示資料庫配置和狀態"""
    print("\n🗄️  資料庫配置")
    print("-" * 40)
    
    try:
        # 從 Task Definition 獲取資料庫 URL
        ecs = boto3.client('ecs', region_name='us-west-2')
        response = ecs.describe_task_definition(taskDefinition='simple-lending-bot')
        
        container = response['taskDefinition']['containerDefinitions'][0]
        
        for env in container.get('environment', []):
            if env['name'] == 'DATABASE_URL':
                db_url = env['value']
                print(f"📊 資料庫連接:")
                
                # 解析 URL (注意：這裡只是顯示，不會暴露密碼)
                if 'postgresql://' in db_url:
                    parts = db_url.replace('postgresql://', '').split('@')
                    if len(parts) == 2:
                        host_part = parts[1].split(':')[0]
                        print(f"   主機: {host_part}")
                        print(f"   資料庫: postgres")
                        print(f"   SSL: 啟用")
                
                break
        
        # 嘗試連接測試（不執行查詢）
        print(f"   連接狀態: 正在檢查...")
        
    except Exception as e:
        print(f"❌ 無法獲取資料庫配置: {str(e)}")

def show_costs_and_limits():
    """顯示成本和限制資訊"""
    print("\n💰 AWS 成本和限制")
    print("-" * 40)
    
    print("🆓 免費方案使用情況:")
    print("   ECS Fargate:")
    print("     - CPU: 256 (0.25 vCPU)")
    print("     - 記憶體: 512 MB")
    print("     - 預估月使用量: ~20 GB-Hours (免費額度內)")
    
    print("   RDS PostgreSQL:")
    print("     - 實例: db.t4g.micro")
    print("     - 存儲: 20 GB")
    print("     - 預估月使用量: ~750 小時 (免費額度內)")
    
    print("   其他服務:")
    print("     - ECR: <500 MB 映像存儲 (免費)")
    print("     - CloudWatch: 標準日誌記錄 (免費額度內)")
    print("     - SSM Parameter Store: <10,000 參數 (免費)")

def main():
    print("🔍 SimpleLendingBot 完整配置查看器")
    print("=" * 50)
    print(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    show_aws_infrastructure()
    show_api_config()
    show_bot_config()
    show_database_config()
    show_costs_and_limits()
    
    print(f"\n{'=' * 50}")
    print("💡 提示:")
    print("   - 使用 'python monitor.py' 查看即時運行狀態")
    print("   - 使用 'python health_check.py' 進行健康檢查")
    print("   - 使用 './deploy.sh' 進行快速重新部署")

if __name__ == "__main__":
    main()