#!/usr/bin/env python3
"""
SimpleLendingBot AWS 監控腳本
用於本地監控雲端 Bot 運行狀態
"""

import boto3
import json
import time
from datetime import datetime, timezone
import sys

def get_ecs_status():
    """獲取 ECS 服務狀態"""
    ecs = boto3.client('ecs', region_name='us-west-2')
    
    try:
        response = ecs.describe_services(
            cluster='simple-lending-bot-cluster',
            services=['simple-lending-bot-service']
        )
        
        service = response['services'][0]
        return {
            'status': service['status'],
            'running_count': service['runningCount'],
            'desired_count': service['desiredCount'],
            'deployment_status': service['deployments'][0]['rolloutState']
        }
    except Exception as e:
        return {'error': str(e)}

def get_recent_logs(lines=20):
    """獲取最近的日誌"""
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
            return {'error': 'No log streams found'}
        
        stream_name = streams['logStreams'][0]['logStreamName']
        
        # 獲取日誌事件
        events = logs.get_log_events(
            logGroupName='/ecs/simple-lending-bot',
            logStreamName=stream_name,
            limit=lines,
            startFromHead=False
        )
        
        return [event['message'] for event in events['events']]
    
    except Exception as e:
        return {'error': str(e)}

def get_rds_status():
    """獲取 RDS 狀態"""
    rds = boto3.client('rds', region_name='us-west-2')
    
    try:
        response = rds.describe_db_instances(
            DBInstanceIdentifier='simple-lending-bot-db'
        )
        
        db = response['DBInstances'][0]
        return {
            'status': db['DBInstanceStatus'],
            'engine': db['Engine'],
            'endpoint': db['Endpoint']['Address'] if 'Endpoint' in db else 'N/A'
        }
    except Exception as e:
        return {'error': str(e)}

def main():
    print("🤖 SimpleLendingBot AWS 監控儀表板")
    print("=" * 50)
    
    # ECS 狀態
    print("\n📊 ECS Fargate 服務狀態:")
    ecs_status = get_ecs_status()
    if 'error' in ecs_status:
        print(f"❌ 錯誤: {ecs_status['error']}")
    else:
        print(f"   狀態: {ecs_status['status']}")
        print(f"   運行數量: {ecs_status['running_count']}/{ecs_status['desired_count']}")
        print(f"   部署狀態: {ecs_status['deployment_status']}")
    
    # RDS 狀態
    print("\n💾 PostgreSQL 資料庫狀態:")
    rds_status = get_rds_status()
    if 'error' in rds_status:
        print(f"❌ 錯誤: {rds_status['error']}")
    else:
        print(f"   狀態: {rds_status['status']}")
        print(f"   引擎: {rds_status['engine']}")
        print(f"   端點: {rds_status['endpoint']}")
    
    # 最近日誌
    print("\n📝 最近日誌 (最新20條):")
    logs = get_recent_logs()
    if isinstance(logs, dict) and 'error' in logs:
        print(f"❌ 錯誤: {logs['error']}")
    else:
        for log in logs[-10:]:  # 只顯示最新10條
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"   {log.strip()}")
    
    print(f"\n⏰ 更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "watch":
        # 監控模式 - 每30秒刷新
        while True:
            try:
                print("\033[2J\033[H")  # 清屏
                main()
                time.sleep(30)
            except KeyboardInterrupt:
                print("\n\n👋 監控已停止")
                break
    else:
        main()