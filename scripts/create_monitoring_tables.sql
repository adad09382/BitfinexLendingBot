-- 創建監控相關的表
-- 用於存儲系統監控指標和告警記錄

-- 監控指標表
CREATE TABLE IF NOT EXISTS monitoring_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metric_type VARCHAR(50) NOT NULL,
    metric_data JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 告警記錄表
CREATE TABLE IF NOT EXISTS alert_logs (
    id SERIAL PRIMARY KEY,
    alert_level VARCHAR(20) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    alert_message TEXT NOT NULL,
    alert_data JSONB,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 系統健康快照表
CREATE TABLE IF NOT EXISTS health_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- 系統指標
    cpu_percent NUMERIC(5,2),
    memory_percent NUMERIC(5,2),
    disk_percent NUMERIC(5,2),
    
    -- 資料庫指標
    db_connections INTEGER,
    db_size_mb BIGINT,
    
    -- 應用指標
    error_count_hour INTEGER DEFAULT 0,
    warning_count_hour INTEGER DEFAULT 0,
    
    -- 結算狀態
    latest_settlement_date DATE,
    settlement_status VARCHAR(20),
    settlement_delay_hours NUMERIC(6,2),
    
    -- 整體健康狀態
    overall_status VARCHAR(20) DEFAULT 'UNKNOWN',
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 性能基準表
CREATE TABLE IF NOT EXISTS performance_baselines (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL UNIQUE,
    baseline_value NUMERIC(15,6) NOT NULL,
    threshold_warning NUMERIC(15,6),
    threshold_critical NUMERIC(15,6),
    unit VARCHAR(20),
    description TEXT,
    last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 創建索引
CREATE INDEX IF NOT EXISTS idx_monitoring_metrics_timestamp ON monitoring_metrics(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_monitoring_metrics_type ON monitoring_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_alert_logs_created_at ON alert_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alert_logs_level ON alert_logs(alert_level);
CREATE INDEX IF NOT EXISTS idx_alert_logs_resolved ON alert_logs(resolved);
CREATE INDEX IF NOT EXISTS idx_health_snapshots_time ON health_snapshots(snapshot_time DESC);
CREATE INDEX IF NOT EXISTS idx_health_snapshots_status ON health_snapshots(overall_status);

-- 插入預設性能基準
INSERT INTO performance_baselines (metric_name, baseline_value, threshold_warning, threshold_critical, unit, description) VALUES
    ('cpu_percent', 50.0, 80.0, 95.0, '%', 'CPU usage percentage'),
    ('memory_percent', 60.0, 85.0, 95.0, '%', 'Memory usage percentage'),
    ('disk_percent', 40.0, 85.0, 95.0, '%', 'Disk usage percentage'),
    ('db_connections', 10, 80, 95, 'count', 'Active database connections'),
    ('settlement_delay_hours', 1.0, 25.0, 48.0, 'hours', 'Daily settlement delay'),
    ('error_rate_per_hour', 0.0, 5.0, 10.0, 'count', 'Application errors per hour'),
    ('api_response_time_ms', 500.0, 2000.0, 5000.0, 'ms', 'Average API response time')
ON CONFLICT (metric_name) DO NOTHING;

-- 創建視圖用於監控儀表板
CREATE OR REPLACE VIEW monitoring_dashboard AS
SELECT 
    h.snapshot_time,
    h.cpu_percent,
    h.memory_percent,
    h.disk_percent,
    h.db_connections,
    h.db_size_mb,
    h.error_count_hour,
    h.warning_count_hour,
    h.latest_settlement_date,
    h.settlement_status,
    h.settlement_delay_hours,
    h.overall_status,
    
    -- 與基準值比較
    CASE 
        WHEN h.cpu_percent > pb_cpu.threshold_critical THEN 'CRITICAL'
        WHEN h.cpu_percent > pb_cpu.threshold_warning THEN 'WARNING'
        ELSE 'OK'
    END as cpu_status,
    
    CASE 
        WHEN h.memory_percent > pb_mem.threshold_critical THEN 'CRITICAL'
        WHEN h.memory_percent > pb_mem.threshold_warning THEN 'WARNING'
        ELSE 'OK'
    END as memory_status,
    
    CASE 
        WHEN h.disk_percent > pb_disk.threshold_critical THEN 'CRITICAL'
        WHEN h.disk_percent > pb_disk.threshold_warning THEN 'WARNING'
        ELSE 'OK'
    END as disk_status
    
FROM health_snapshots h
LEFT JOIN performance_baselines pb_cpu ON pb_cpu.metric_name = 'cpu_percent'
LEFT JOIN performance_baselines pb_mem ON pb_mem.metric_name = 'memory_percent'
LEFT JOIN performance_baselines pb_disk ON pb_disk.metric_name = 'disk_percent'
ORDER BY h.snapshot_time DESC;

-- 創建清理舊數據的函數
CREATE OR REPLACE FUNCTION cleanup_old_monitoring_data()
RETURNS void AS $$
BEGIN
    -- 清理30天前的監控指標
    DELETE FROM monitoring_metrics 
    WHERE created_at < NOW() - INTERVAL '30 days';
    
    -- 清理90天前的已解決告警
    DELETE FROM alert_logs 
    WHERE resolved = TRUE AND created_at < NOW() - INTERVAL '90 days';
    
    -- 清理7天前的健康快照 (保留每小時一個)
    DELETE FROM health_snapshots 
    WHERE created_at < NOW() - INTERVAL '7 days'
    AND id NOT IN (
        SELECT MIN(id) 
        FROM health_snapshots 
        WHERE created_at < NOW() - INTERVAL '7 days'
        GROUP BY DATE_TRUNC('hour', created_at)
    );
    
    -- 記錄清理操作
    INSERT INTO alert_logs (alert_level, alert_type, alert_message) VALUES
        ('INFO', 'MAINTENANCE', 'Completed monitoring data cleanup');
END;
$$ LANGUAGE plpgsql;

-- 權限設置
GRANT ALL PRIVILEGES ON monitoring_metrics TO bitfinex_user;
GRANT ALL PRIVILEGES ON alert_logs TO bitfinex_user;
GRANT ALL PRIVILEGES ON health_snapshots TO bitfinex_user;
GRANT ALL PRIVILEGES ON performance_baselines TO bitfinex_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO bitfinex_user;