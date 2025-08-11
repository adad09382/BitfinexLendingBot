#!/usr/bin/env python3
"""
BitfinexLendingBot 監控腳本
收集性能指標並發送告警
"""

import sys
import os
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
import psutil
import requests

# 添加項目路徑
sys.path.insert(0, '/app')

try:
    from src.main.python.services.database_manager import DatabaseManager
    from src.main.python.core.config import get_config_manager
    from src.main.python.utils.notification_manager import NotificationManager
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

class SystemMonitor:
    """系統監控器"""
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self.db_manager = DatabaseManager(self.config_manager.config.database)
        self.notification_manager = NotificationManager(
            telegram_bot_token=self.config_manager.config.api.telegram_bot_token,
            telegram_chat_id=self.config_manager.config.api.telegram_chat_id
        )
        
        # 告警閾值
        self.thresholds = {
            'memory_percent': 85.0,
            'disk_percent': 85.0,
            'cpu_percent': 80.0,
            'db_connections': 80,
            'settlement_delay_hours': 25,  # 每日結算延遲超過25小時告警
            'api_error_rate': 10.0  # API 錯誤率超過10%告警
        }
        
        # 設置日誌
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/app/logs/monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """收集系統指標"""
        try:
            # CPU 使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 內存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / (1024**3)
            
            # 磁盤使用率
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_free_gb = disk.free / (1024**3)
            
            # 網絡統計
            network = psutil.net_io_counters()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'memory_available_gb': round(memory_available_gb, 2),
                'disk_percent': disk_percent,
                'disk_free_gb': round(disk_free_gb, 2),
                'network_bytes_sent': network.bytes_sent,
                'network_bytes_recv': network.bytes_recv
            }
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
            return {}
    
    def collect_database_metrics(self) -> Dict[str, Any]:
        """收集資料庫指標"""
        try:
            connection = self.db_manager.get_connection()
            cursor = connection.cursor()
            
            # 連接數量
            cursor.execute("""
                SELECT count(*) as active_connections
                FROM pg_stat_activity 
                WHERE state = 'active'
            """)
            active_connections = cursor.fetchone()[0]
            
            # 資料庫大小
            cursor.execute("""
                SELECT pg_size_pretty(pg_database_size('bitfinex_bot')) as db_size
            """)
            db_size = cursor.fetchone()[0]
            
            # 表統計
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    n_tup_ins,
                    n_tup_upd,
                    n_tup_del
                FROM pg_stat_user_tables
                WHERE tablename IN ('daily_earnings', 'active_positions', 'lending_orders')
            """)
            table_stats = cursor.fetchall()
            
            # 最近的每日結算
            cursor.execute("""
                SELECT date, settlement_status, created_at
                FROM daily_earnings
                ORDER BY date DESC
                LIMIT 1
            """)
            latest_settlement = cursor.fetchone()
            
            cursor.close()
            connection.close()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'active_connections': active_connections,
                'database_size': db_size,
                'table_stats': table_stats,
                'latest_settlement': {
                    'date': latest_settlement[0].isoformat() if latest_settlement else None,
                    'status': latest_settlement[1] if latest_settlement else None,
                    'created_at': latest_settlement[2].isoformat() if latest_settlement else None
                } if latest_settlement else None
            }
        except Exception as e:
            self.logger.error(f"Failed to collect database metrics: {e}")
            return {}
    
    def collect_application_metrics(self) -> Dict[str, Any]:
        """收集應用指標"""
        try:
            # 檢查日誌文件中的錯誤
            log_file = '/app/logs/bot.log'
            error_count = 0
            warning_count = 0
            
            if os.path.exists(log_file):
                # 檢查最近1小時的日誌
                one_hour_ago = datetime.now() - timedelta(hours=1)
                
                with open(log_file, 'r') as f:
                    for line in f:
                        if 'ERROR' in line:
                            error_count += 1
                        elif 'WARNING' in line:
                            warning_count += 1
            
            # 檢查進程狀態
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent']):
                if 'python' in proc.info['name'].lower():
                    processes.append(proc.info)
            
            return {
                'timestamp': datetime.now().isoformat(),
                'error_count_last_hour': error_count,
                'warning_count_last_hour': warning_count,
                'python_processes': processes
            }
        except Exception as e:
            self.logger.error(f"Failed to collect application metrics: {e}")
            return {}
    
    def check_settlement_health(self) -> Dict[str, Any]:
        """檢查每日結算健康狀態"""
        try:
            connection = self.db_manager.get_connection()
            cursor = connection.cursor()
            
            # 檢查最近的結算狀態
            cursor.execute("""
                SELECT 
                    date,
                    settlement_status,
                    created_at,
                    EXTRACT(EPOCH FROM (NOW() - created_at))/3600 as hours_since_created
                FROM daily_earnings
                WHERE date >= CURRENT_DATE - INTERVAL '2 days'
                ORDER BY date DESC
            """)
            recent_settlements = cursor.fetchall()
            
            cursor.close()
            connection.close()
            
            issues = []
            
            # 檢查是否有失敗的結算
            for settlement in recent_settlements:
                date, status, created_at, hours_since = settlement
                
                if status == 'FAILED':
                    issues.append(f"Settlement failed for {date}")
                elif status == 'PENDING' and hours_since > self.thresholds['settlement_delay_hours']:
                    issues.append(f"Settlement delayed for {date} ({hours_since:.1f}h)")
            
            # 檢查是否缺少今日結算記錄
            today = datetime.now().date()
            today_settlement = next((s for s in recent_settlements if s[0] == today), None)
            
            if not today_settlement:
                current_hour = datetime.now().hour
                if current_hour > 1:  # 凌晨1點後還沒有今日記錄
                    issues.append(f"No settlement record for today ({today})")
            
            return {
                'timestamp': datetime.now().isoformat(),
                'recent_settlements': len(recent_settlements),
                'issues': issues,
                'status': 'HEALTHY' if not issues else 'WARNING'
            }
        except Exception as e:
            self.logger.error(f"Failed to check settlement health: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    def send_alerts(self, metrics: Dict[str, Any]):
        """發送告警"""
        alerts = []
        
        # 系統資源告警
        system_metrics = metrics.get('system', {})
        if system_metrics.get('memory_percent', 0) > self.thresholds['memory_percent']:
            alerts.append(f"⚠️ High memory usage: {system_metrics['memory_percent']:.1f}%")
        
        if system_metrics.get('disk_percent', 0) > self.thresholds['disk_percent']:
            alerts.append(f"⚠️ High disk usage: {system_metrics['disk_percent']:.1f}%")
        
        if system_metrics.get('cpu_percent', 0) > self.thresholds['cpu_percent']:
            alerts.append(f"⚠️ High CPU usage: {system_metrics['cpu_percent']:.1f}%")
        
        # 資料庫告警
        db_metrics = metrics.get('database', {})
        if db_metrics.get('active_connections', 0) > self.thresholds['db_connections']:
            alerts.append(f"⚠️ High DB connections: {db_metrics['active_connections']}")
        
        # 應用告警
        app_metrics = metrics.get('application', {})
        if app_metrics.get('error_count_last_hour', 0) > 5:
            alerts.append(f"⚠️ High error rate: {app_metrics['error_count_last_hour']} errors/hour")
        
        # 結算健康告警
        settlement_health = metrics.get('settlement_health', {})
        if settlement_health.get('status') != 'HEALTHY':
            for issue in settlement_health.get('issues', []):
                alerts.append(f"❌ Settlement issue: {issue}")
        
        # 發送告警
        if alerts:
            alert_message = "🚨 BitfinexLendingBot Alerts:\n\n" + "\n".join(alerts)
            try:
                self.notification_manager.send_alert(alert_message, level="WARNING")
                self.logger.warning(f"Sent {len(alerts)} alerts")
            except Exception as e:
                self.logger.error(f"Failed to send alerts: {e}")
    
    def save_metrics(self, metrics: Dict[str, Any]):
        """保存指標到資料庫"""
        try:
            connection = self.db_manager.get_connection()
            cursor = connection.cursor()
            
            # 保存到 monitoring_metrics 表 (如果存在)
            cursor.execute("""
                INSERT INTO monitoring_metrics (
                    timestamp, metric_type, metric_data
                ) VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                datetime.now(),
                'system_health',
                json.dumps(metrics)
            ))
            
            connection.commit()
            cursor.close()
            connection.close()
            
        except Exception as e:
            # 如果表不存在，只記錄到日誌
            self.logger.debug(f"Could not save metrics to database: {e}")
    
    def run_monitoring_cycle(self):
        """執行一次監控週期"""
        self.logger.info("Starting monitoring cycle")
        
        # 收集所有指標
        metrics = {
            'system': self.collect_system_metrics(),
            'database': self.collect_database_metrics(),
            'application': self.collect_application_metrics(),
            'settlement_health': self.check_settlement_health()
        }
        
        # 發送告警
        self.send_alerts(metrics)
        
        # 保存指標
        self.save_metrics(metrics)
        
        # 記錄摘要
        self.logger.info(f"Monitoring cycle completed: "
                        f"Memory: {metrics['system'].get('memory_percent', 0):.1f}%, "
                        f"Disk: {metrics['system'].get('disk_percent', 0):.1f}%, "
                        f"DB: {metrics['database'].get('active_connections', 0)} connections, "
                        f"Settlement: {metrics['settlement_health'].get('status', 'UNKNOWN')}")
        
        return metrics

def main():
    """主函數"""
    monitor = SystemMonitor()
    
    # 如果是一次性執行
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        metrics = monitor.run_monitoring_cycle()
        print(json.dumps(metrics, indent=2, default=str))
        return
    
    # 持續監控模式
    monitor.logger.info("Starting continuous monitoring")
    
    try:
        while True:
            monitor.run_monitoring_cycle()
            time.sleep(300)  # 每5分鐘執行一次
    except KeyboardInterrupt:
        monitor.logger.info("Monitoring stopped by user")
    except Exception as e:
        monitor.logger.error(f"Monitoring error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()