#!/usr/bin/env python3
"""
SimpleLendingBot 完整健康檢查
檢查所有關鍵組件的運行狀態
"""

import boto3
import json
from datetime import datetime, timezone
import sys

def check_ecs_service():
    """檢查 ECS 服務狀態"""
    ecs = boto3.client('ecs', region_name='us-west-2')
    
    try:
        response = ecs.describe_services(
            cluster='simple-lending-bot-cluster',
            services=['simple-lending-bot-service']
        )
        
        service = response['services'][0]
        deployment = service['deployments'][0]
        
        status = {
            'service_status': service['status'],
            'running_count': service['runningCount'],
            'desired_count': service['desiredCount'],
            'deployment_status': deployment['rolloutState'],
            'healthy': service['runningCount'] == service['desiredCount'] and service['status'] == 'ACTIVE'
        }
        
        return status
    except Exception as e:
        return {'error': str(e), 'healthy': False}

def check_rds_database():
    """檢查 RDS 資料庫狀態"""
    rds = boto3.client('rds', region_name='us-west-2')
    
    try:
        response = rds.describe_db_instances(
            DBInstanceIdentifier='simple-lending-bot-db'
        )
        
        db = response['DBInstances'][0]
        status = {
            'status': db['DBInstanceStatus'],
            'healthy': db['DBInstanceStatus'] == 'available'
        }
        
        return status
    except Exception as e:
        return {'error': str(e), 'healthy': False}

def check_recent_activity():
    """檢查最近的 Bot 活動"""
    logs = boto3.client('logs', region_name='us-west-2')
    
    try:
        # 獲取最新的 log stream
        streams = logs.describe_log_streams(
            logGroupName='/ecs/simple-lending-bot',
            orderBy='LastEventTime',
            descending=True,
            limit=1
        )
        
        if not streams['logStreams']:
            return {'error': 'No log streams found', 'healthy': False}
        
        stream = streams['logStreams'][0]
        last_event_time = stream.get('lastEventTime')
        
        if last_event_time:
            last_event = datetime.fromtimestamp(last_event_time / 1000, tz=timezone.utc)
            now = datetime.now(tz=timezone.utc)
            minutes_ago = (now - last_event).total_seconds() / 60
            
            # 如果超過 60 分鐘沒有日誌，可能有問題
            healthy = minutes_ago < 60
            
            return {
                'last_activity': last_event.strftime('%Y-%m-%d %H:%M:%S UTC'),
                'minutes_ago': round(minutes_ago, 1),
                'healthy': healthy
            }
        else:
            return {'error': 'No recent activity', 'healthy': False}
            
    except Exception as e:
        return {'error': str(e), 'healthy': False}

def check_api_credentials():
    """檢查 API 憑證配置"""
    ssm = boto3.client('ssm', region_name='us-west-2')
    
    try:
        # 檢查 SSM 參數是否存在
        response = ssm.describe_parameters(
            Filters=[
                {
                    'Key': 'Name',
                    'Values': ['/simple-lending-bot/']
                }
            ]
        )
        
        params = [p['Name'] for p in response['Parameters']]
        required_params = ['/simple-lending-bot/BITFINEX_API_KEY', '/simple-lending-bot/BITFINEX_API_SECRET']
        
        missing = [p for p in required_params if p not in params]
        
        return {
            'parameters_found': len(params),
            'required_parameters': len(required_params),
            'missing_parameters': missing,
            'healthy': len(missing) == 0
        }
        
    except Exception as e:
        return {'error': str(e), 'healthy': False}

def check_task_permissions():
    """檢查 Task Definition 權限配置"""
    ecs = boto3.client('ecs', region_name='us-west-2')
    
    try:
        response = ecs.describe_task_definition(taskDefinition='simple-lending-bot')
        task_def = response['taskDefinition']
        
        has_execution_role = 'executionRoleArn' in task_def
        has_task_role = 'taskRoleArn' in task_def
        has_secrets = len(task_def['containerDefinitions'][0].get('secrets', [])) > 0
        
        return {
            'has_execution_role': has_execution_role,
            'has_task_role': has_task_role,
            'has_secrets_config': has_secrets,
            'secrets_count': len(task_def['containerDefinitions'][0].get('secrets', [])),
            'healthy': has_execution_role and has_secrets
        }
        
    except Exception as e:
        return {'error': str(e), 'healthy': False}

def main():
    print("🔍 SimpleLendingBot 完整健康檢查")
    print("=" * 50)
    
    checks = [
        ("ECS 服務狀態", check_ecs_service),
        ("RDS 資料庫", check_rds_database),
        ("最近活動", check_recent_activity),
        ("API 憑證", check_api_credentials),
        ("權限配置", check_task_permissions)
    ]
    
    all_healthy = True
    
    for name, check_func in checks:
        print(f"\n🔧 {name}:")
        result = check_func()
        
        if result.get('healthy', False):
            print("   ✅ 正常")
        else:
            print("   ❌ 有問題")
            all_healthy = False
        
        # 顯示詳細信息
        for key, value in result.items():
            if key != 'healthy':
                print(f"   {key}: {value}")
    
    print("\n" + "=" * 50)
    if all_healthy:
        print("🎉 所有檢查通過！Bot 運行正常")
        sys.exit(0)
    else:
        print("⚠️  發現問題，需要修復")
        sys.exit(1)

if __name__ == "__main__":
    main()