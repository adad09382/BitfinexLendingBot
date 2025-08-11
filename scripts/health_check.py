#!/usr/bin/env python3
"""
BitfinexLendingBot 健康檢查腳本
用於 Docker 容器健康狀態檢查
"""

import sys
import os
import time
import logging
from datetime import datetime, timedelta
import psutil

# 添加項目路徑
sys.path.insert(0, '/app')

try:
    from src.main.python.services.database_manager import DatabaseManager
    from src.main.python.core.config import get_config_manager
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

def check_process_health():
    """檢查進程健康狀態"""
    try:
        # 檢查內存使用率
        memory_percent = psutil.virtual_memory().percent
        if memory_percent > 90:
            print(f"WARN: High memory usage: {memory_percent}%")
            return False
            
        # 檢查磁盤使用率
        disk_percent = psutil.disk_usage('/').percent
        if disk_percent > 90:
            print(f"WARN: High disk usage: {disk_percent}%")
            return False
            
        return True
    except Exception as e:
        print(f"Process health check failed: {e}")
        return False

def check_database_connection():
    """檢查數據庫連接"""
    try:
        config_manager = get_config_manager()
        db_manager = DatabaseManager(config_manager.config.database)
        
        # 簡單的連接測試
        connection = db_manager.get_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        return result[0] == 1
    except Exception as e:
        print(f"Database health check failed: {e}")
        return False

def check_log_file_freshness():
    """檢查日誌文件是否新鮮 (確保應用在運行)"""
    try:
        log_file = "/app/logs/bot.log"
        if not os.path.exists(log_file):
            print("Log file does not exist")
            return False
            
        # 檢查日誌文件最後修改時間
        last_modified = datetime.fromtimestamp(os.path.getmtime(log_file))
        time_diff = datetime.now() - last_modified
        
        # 如果日誌文件超過5分鐘沒有更新，認為不健康
        if time_diff > timedelta(minutes=5):
            print(f"Log file is stale: last modified {time_diff} ago")
            return False
            
        return True
    except Exception as e:
        print(f"Log freshness check failed: {e}")
        return False

def check_critical_errors():
    """檢查是否有關鍵錯誤"""
    try:
        log_file = "/app/logs/bot.log"
        if not os.path.exists(log_file):
            return True  # 沒有日誌文件不算錯誤
            
        # 檢查最近的日誌是否有CRITICAL錯誤
        with open(log_file, 'r') as f:
            lines = f.readlines()
            
        # 檢查最後100行
        recent_lines = lines[-100:] if len(lines) > 100 else lines
        
        for line in recent_lines:
            if 'CRITICAL' in line:
                print(f"Found critical error in logs: {line.strip()}")
                return False
                
        return True
    except Exception as e:
        print(f"Critical error check failed: {e}")
        return True  # 檢查失敗不算應用不健康

def main():
    """主健康檢查函數"""
    print(f"Health check started at {datetime.now()}")
    
    checks = [
        ("Process Health", check_process_health),
        ("Database Connection", check_database_connection),
        ("Log File Freshness", check_log_file_freshness),
        ("Critical Errors", check_critical_errors)
    ]
    
    all_healthy = True
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            status = "PASS" if result else "FAIL"
            print(f"{check_name}: {status}")
            
            if not result:
                all_healthy = False
        except Exception as e:
            print(f"{check_name}: ERROR - {e}")
            all_healthy = False
    
    if all_healthy:
        print("Overall health: HEALTHY")
        sys.exit(0)
    else:
        print("Overall health: UNHEALTHY")
        sys.exit(1)

if __name__ == "__main__":
    main()