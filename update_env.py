#!/usr/bin/env python3
"""
更新 AWS Systems Manager Parameter Store 中的環境變數
用於安全地管理 API 密鑰等敏感資料
"""

import boto3
import json
import sys
from getpass import getpass

def update_parameter(name, value, description="", parameter_type="SecureString"):
    """更新 SSM Parameter"""
    ssm = boto3.client('ssm', region_name='us-west-2')
    
    try:
        ssm.put_parameter(
            Name=f'/simple-lending-bot/{name}',
            Value=value,
            Type=parameter_type,
            Description=description,
            Overwrite=True
        )
        print(f"✅ 成功更新參數: {name}")
        return True
    except Exception as e:
        print(f"❌ 更新失敗 {name}: {str(e)}")
        return False

def list_parameters():
    """列出所有 bot 參數"""
    ssm = boto3.client('ssm', region_name='us-west-2')
    
    try:
        response = ssm.describe_parameters(
            Filters=[
                {
                    'Key': 'Name',
                    'Values': ['/simple-lending-bot/']
                }
            ]
        )
        
        print("📋 當前環境變數:")
        for param in response['Parameters']:
            name = param['Name'].replace('/simple-lending-bot/', '')
            print(f"   {name}: {param['Type']}")
    except Exception as e:
        print(f"❌ 列出參數失敗: {str(e)}")

def update_task_definition_with_ssm():
    """更新 Task Definition 使用 SSM 參數"""
    ecs = boto3.client('ecs', region_name='us-west-2')
    
    # 讀取當前 task definition
    response = ecs.describe_task_definition(taskDefinition='simple-lending-bot')
    task_def = response['taskDefinition']
    
    # 移除不需要的字段
    for key in ['taskDefinitionArn', 'revision', 'status', 'requiresAttributes', 'placementConstraints', 'compatibilities', 'registeredAt', 'registeredBy']:
        task_def.pop(key, None)
    
    # 更新環境變數使用 SSM
    container = task_def['containerDefinitions'][0]
    container['secrets'] = [
        {
            'name': 'BITFINEX_API_KEY',
            'valueFrom': '/simple-lending-bot/BITFINEX_API_KEY'
        },
        {
            'name': 'BITFINEX_API_SECRET',
            'valueFrom': '/simple-lending-bot/BITFINEX_API_SECRET'
        }
    ]
    
    # 保留非敏感環境變數
    container['environment'] = [
        env for env in container.get('environment', [])
        if env['name'] not in ['BITFINEX_API_KEY', 'BITFINEX_API_SECRET']
    ]
    
    try:
        ecs.register_task_definition(**task_def)
        print("✅ Task Definition 更新成功")
        return True
    except Exception as e:
        print(f"❌ Task Definition 更新失敗: {str(e)}")
        return False

def main():
    print("🔐 SimpleLendingBot 環境變數管理")
    print("=" * 40)
    
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python update_env.py list                    # 列出當前參數")
        print("  python update_env.py set <名稱> [值]          # 設置參數")
        print("  python update_env.py update-task-def         # 更新 Task Definition")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        list_parameters()
    
    elif command == "set":
        if len(sys.argv) < 3:
            print("❌ 請提供參數名稱")
            return
        
        name = sys.argv[2]
        
        if len(sys.argv) > 3:
            value = sys.argv[3]
        else:
            value = getpass(f"請輸入 {name} 的值 (輸入時不會顯示): ")
        
        description = f"SimpleLendingBot {name} parameter"
        update_parameter(name, value, description)
    
    elif command == "update-task-def":
        update_task_definition_with_ssm()
        
        # 更新 ECS 服務以使用新的 Task Definition
        ecs = boto3.client('ecs', region_name='us-west-2')
        try:
            ecs.update_service(
                cluster='simple-lending-bot-cluster',
                service='simple-lending-bot-service',
                forceNewDeployment=True
            )
            print("✅ ECS 服務更新成功，正在重新部署...")
        except Exception as e:
            print(f"❌ ECS 服務更新失敗: {str(e)}")
    
    else:
        print(f"❌ 未知命令: {command}")

if __name__ == "__main__":
    main()