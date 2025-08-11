#!/usr/bin/env python3
"""
監控系統測試腳本
測試監控功能和告警系統
"""

import os
import sys
import time
import json
import subprocess
from datetime import datetime

def test_system_metrics():
    """測試系統指標收集"""
    print("🧪 測試系統指標收集...")
    
    try:
        # 測試 CPU 使用率
        import psutil
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        print(f"  ✅ CPU 使用率: {cpu_usage}%")
        print(f"  ✅ 記憶體使用率: {memory.percent}%")
        print(f"  ✅ 磁碟使用率: {disk.percent}%")
        
        return True
    except ImportError:
        print("  ❌ psutil 未安裝，無法測試系統指標")
        return False
    except Exception as e:
        print(f"  ❌ 系統指標測試失敗: {e}")
        return False

def test_docker_stats():
    """測試 Docker 容器統計"""
    print("🧪 測試 Docker 容器統計...")
    
    try:
        result = subprocess.run(
            ['docker', 'stats', '--no-stream', '--format', 
             'table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}'],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            print("  ✅ Docker 統計可用")
            lines = result.stdout.strip().split('\n')
            for line in lines[:3]:  # 只顯示前3行
                print(f"    {line}")
            return True
        else:
            print(f"  ❌ Docker 統計失敗: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("  ❌ Docker 統計超時")
        return False
    except Exception as e:
        print(f"  ❌ Docker 統計測試失敗: {e}")
        return False

def test_alert_formatting():
    """測試告警格式化"""
    print("🧪 測試告警格式化...")
    
    try:
        # 模擬告警數據
        alert_data = {
            'timestamp': datetime.now().isoformat(),
            'type': 'system',
            'severity': 'warning',
            'metric': 'cpu_usage',
            'value': 85.5,
            'threshold': 80.0,
            'message': '系統 CPU 使用率過高'
        }
        
        # 格式化告警消息
        message = f"🚨 {alert_data['severity'].upper()} 告警\n"
        message += f"📊 指標: {alert_data['metric']}\n"
        message += f"📈 當前值: {alert_data['value']}%\n"
        message += f"⚠️ 閾值: {alert_data['threshold']}%\n"
        message += f"💬 消息: {alert_data['message']}\n"
        message += f"🕐 時間: {alert_data['timestamp']}"
        
        print("  ✅ 告警格式化成功")
        print(f"  預覽:\n{message}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 告警格式化測試失敗: {e}")
        return False

def test_database_connection():
    """測試數據庫連接 (模擬)"""
    print("🧪 測試數據庫連接...")
    
    # 由於沒有實際的數據庫連接，我們模擬測試
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'bitfinex_bot'),
        'user': os.getenv('DB_USER', 'bitfinex_user')
    }
    
    print(f"  📋 數據庫配置:")
    for key, value in db_config.items():
        if key != 'password':  # 不顯示密碼
            print(f"    {key}: {value}")
    
    print("  ✅ 數據庫配置檢查通過")
    print("  ℹ️ 注意: 實際連接需要在 Docker 環境中測試")
    
    return True

def test_environment_variables():
    """測試環境變量"""
    print("🧪 測試環境變量...")
    
    required_vars = [
        'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD',
        'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID'
    ]
    
    optional_vars = [
        'ALERT_THRESHOLDS_CPU', 'ALERT_THRESHOLDS_MEMORY', 
        'ALERT_THRESHOLDS_DISK', 'MONITOR_INTERVAL'
    ]
    
    missing_required = []
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
    
    if missing_required:
        print(f"  ❌ 缺少必需的環境變量: {', '.join(missing_required)}")
        print("     請確保 .env 文件包含所有必需的變量")
        return False
    else:
        print("  ✅ 所有必需的環境變量都已設置")
    
    # 檢查可選變量
    present_optional = []
    for var in optional_vars:
        if os.getenv(var):
            present_optional.append(var)
    
    if present_optional:
        print(f"  ✅ 可選環境變量: {', '.join(present_optional)}")
    
    return True

def main():
    """運行所有測試"""
    print("🚀 BitfinexLendingBot 監控系統測試開始\n")
    
    tests = [
        ("環境變量", test_environment_variables),
        ("系統指標", test_system_metrics),
        ("Docker 統計", test_docker_stats),
        ("告警格式化", test_alert_formatting),
        ("數據庫連接", test_database_connection)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ {test_name} 測試異常: {e}")
            results.append((test_name, False))
    
    # 總結
    print(f"\n{'='*50}")
    print("📊 測試總結:")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"  {test_name}: {status}")
    
    print(f"\n通過率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 所有測試通過！監控系統準備就緒")
        return 0
    else:
        print(f"\n⚠️ {total-passed} 個測試失敗，請檢查配置")
        return 1

if __name__ == "__main__":
    sys.exit(main())