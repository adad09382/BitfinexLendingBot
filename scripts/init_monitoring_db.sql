-- 將監控表腳本複製為初始化腳本
-- 這將在數據庫初始化時自動執行

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

-- 創建索引優化查詢性能
CREATE INDEX IF NOT EXISTS idx_monitoring_metrics_timestamp ON monitoring_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_monitoring_metrics_type ON monitoring_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_monitoring_metrics_created_at ON monitoring_metrics(created_at);

-- 告警記錄表
CREATE TABLE IF NOT EXISTS alert_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'info',
    title VARCHAR(200) NOT NULL,
    message TEXT,
    metadata JSONB,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 創建索引
CREATE INDEX IF NOT EXISTS idx_alert_logs_timestamp ON alert_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_alert_logs_type ON alert_logs(alert_type);
CREATE INDEX IF NOT EXISTS idx_alert_logs_severity ON alert_logs(severity);
CREATE INDEX IF NOT EXISTS idx_alert_logs_resolved ON alert_logs(resolved);

-- 系統健康狀態表
CREATE TABLE IF NOT EXISTS system_health (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    service_name VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'unknown',
    cpu_usage DECIMAL(5,2),
    memory_usage DECIMAL(5,2),
    disk_usage DECIMAL(5,2),
    response_time_ms INTEGER,
    error_count INTEGER DEFAULT 0,
    last_error TEXT,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 創建索引
CREATE INDEX IF NOT EXISTS idx_system_health_timestamp ON system_health(timestamp);
CREATE INDEX IF NOT EXISTS idx_system_health_service ON system_health(service_name);
CREATE INDEX IF NOT EXISTS idx_system_health_status ON system_health(status);

-- 性能基準表 - 用於比較和趨勢分析
CREATE TABLE IF NOT EXISTS performance_baselines (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    baseline_value DECIMAL(10,4) NOT NULL,
    unit VARCHAR(20),
    measurement_period VARCHAR(50) NOT NULL, -- 'daily', 'weekly', 'monthly'
    calculated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 創建索引
CREATE INDEX IF NOT EXISTS idx_performance_baselines_metric ON performance_baselines(metric_name);
CREATE INDEX IF NOT EXISTS idx_performance_baselines_period ON performance_baselines(measurement_period);
CREATE INDEX IF NOT EXISTS idx_performance_baselines_calculated_at ON performance_baselines(calculated_at);

-- 清理舊數據的函數
CREATE OR REPLACE FUNCTION cleanup_old_monitoring_data() RETURNS void AS $$
BEGIN
    -- 刪除 30 天前的監控指標
    DELETE FROM monitoring_metrics WHERE created_at < NOW() - INTERVAL '30 days';
    
    -- 刪除 90 天前的已解決告警
    DELETE FROM alert_logs WHERE resolved = TRUE AND resolved_at < NOW() - INTERVAL '90 days';
    
    -- 刪除 7 天前的系統健康記錄
    DELETE FROM system_health WHERE created_at < NOW() - INTERVAL '7 days';
    
    RAISE NOTICE '監控數據清理完成';
END;
$$ LANGUAGE plpgsql;

-- 創建視圖方便查詢
CREATE OR REPLACE VIEW recent_alerts AS
SELECT 
    id,
    timestamp,
    alert_type,
    severity,
    title,
    message,
    resolved,
    created_at
FROM alert_logs 
WHERE created_at >= NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;

CREATE OR REPLACE VIEW system_health_summary AS
SELECT 
    service_name,
    status,
    AVG(cpu_usage) as avg_cpu,
    AVG(memory_usage) as avg_memory,
    AVG(disk_usage) as avg_disk,
    AVG(response_time_ms) as avg_response_time,
    COUNT(*) as health_checks,
    MAX(created_at) as last_check
FROM system_health 
WHERE created_at >= NOW() - INTERVAL '1 hour'
GROUP BY service_name, status
ORDER BY service_name;

-- 授予權限
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bitfinex_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO bitfinex_user;

-- 插入初始化數據
INSERT INTO performance_baselines (metric_name, baseline_value, unit, measurement_period, metadata)
VALUES 
    ('cpu_usage_normal', 25.0, 'percent', 'daily', '{"description": "正常操作時的 CPU 使用率基準"}'),
    ('memory_usage_normal', 30.0, 'percent', 'daily', '{"description": "正常操作時的記憶體使用率基準"}'),
    ('response_time_api', 200.0, 'milliseconds', 'daily', '{"description": "API 響應時間基準"}'),
    ('lending_orders_per_hour', 10.0, 'count', 'hourly', '{"description": "每小時放貸訂單數量基準"}')
ON CONFLICT DO NOTHING;

COMMIT;