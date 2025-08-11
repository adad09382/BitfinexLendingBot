-- BitfinexLendingBot 數據庫初始化腳本
-- 創建所有必要的表和索引

-- 確保使用 UTF-8 編碼
SET client_encoding = 'UTF8';

-- 創建 daily_earnings 表 (核心表)
CREATE TABLE IF NOT EXISTS daily_earnings (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    currency VARCHAR(6) NOT NULL,
    
    -- 用戶關心的核心數據
    total_interest NUMERIC(15,8) NOT NULL DEFAULT 0,
    deployed_amount NUMERIC(15,8) NOT NULL DEFAULT 0,
    available_amount NUMERIC(15,8) NOT NULL DEFAULT 0,
    weighted_avg_rate NUMERIC(10,8) NOT NULL DEFAULT 0,
    
    -- 效果指標
    utilization_rate NUMERIC(5,2) NOT NULL DEFAULT 0,
    daily_return_rate NUMERIC(10,8) NOT NULL DEFAULT 0,
    annualized_return NUMERIC(8,4) NOT NULL DEFAULT 0,
    
    -- 策略信息
    primary_strategy VARCHAR(20) NOT NULL DEFAULT 'NONE',
    total_orders_placed INTEGER NOT NULL DEFAULT 0,
    orders_success_rate NUMERIC(5,2) NOT NULL DEFAULT 0,
    
    -- 市場環境
    market_avg_rate NUMERIC(10,8),
    market_competitiveness NUMERIC(8,4),
    
    -- 元數據
    settlement_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    settlement_timestamp TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- 唯一約束：每天每幣種只能有一條記錄
    UNIQUE(date, currency)
);

-- 創建 active_positions 表
CREATE TABLE IF NOT EXISTS active_positions (
    id SERIAL PRIMARY KEY,
    position_id VARCHAR(50) NOT NULL UNIQUE,
    currency VARCHAR(6) NOT NULL,
    amount NUMERIC(15,8) NOT NULL,
    rate NUMERIC(10,8) NOT NULL,
    period INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    strategy_name VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 創建 lending_orders 表 (保留現有結構)
CREATE TABLE IF NOT EXISTS lending_orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL UNIQUE,
    currency VARCHAR(6) NOT NULL,
    amount NUMERIC(15,8) NOT NULL,
    rate NUMERIC(10,8) NOT NULL,
    period INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    strategy_name VARCHAR(20),
    strategy_params JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 創建 interest_payments 表 (保留現有結構)
CREATE TABLE IF NOT EXISTS interest_payments (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL,
    currency VARCHAR(6) NOT NULL,
    amount NUMERIC(15,8) NOT NULL,
    rate NUMERIC(10,8) NOT NULL,
    payment_date DATE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 創建配置表 (新增)
CREATE TABLE IF NOT EXISTS configurations (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 創建通知日誌表 (新增)
CREATE TABLE IF NOT EXISTS notification_logs (
    id SERIAL PRIMARY KEY,
    message_type VARCHAR(50) NOT NULL,
    recipient VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    sent_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 創建高性能索引
-- daily_earnings 表索引
CREATE INDEX IF NOT EXISTS idx_daily_earnings_date_currency ON daily_earnings(date, currency);
CREATE INDEX IF NOT EXISTS idx_daily_earnings_date_desc ON daily_earnings(date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_earnings_status ON daily_earnings(settlement_status);
CREATE INDEX IF NOT EXISTS idx_daily_earnings_currency_date ON daily_earnings(currency, date DESC);

-- active_positions 表索引
CREATE INDEX IF NOT EXISTS idx_active_positions_status ON active_positions(status);
CREATE INDEX IF NOT EXISTS idx_active_positions_currency ON active_positions(currency);
CREATE INDEX IF NOT EXISTS idx_active_positions_strategy ON active_positions(strategy_name);
CREATE INDEX IF NOT EXISTS idx_active_positions_created_at ON active_positions(created_at DESC);

-- lending_orders 表索引
CREATE INDEX IF NOT EXISTS idx_lending_orders_status ON lending_orders(status);
CREATE INDEX IF NOT EXISTS idx_lending_orders_currency ON lending_orders(currency);
CREATE INDEX IF NOT EXISTS idx_lending_orders_strategy ON lending_orders(strategy_name);
CREATE INDEX IF NOT EXISTS idx_lending_orders_created_at ON lending_orders(created_at DESC);

-- interest_payments 表索引
CREATE INDEX IF NOT EXISTS idx_interest_payments_order_id ON interest_payments(order_id);
CREATE INDEX IF NOT EXISTS idx_interest_payments_date ON interest_payments(payment_date DESC);
CREATE INDEX IF NOT EXISTS idx_interest_payments_currency_date ON interest_payments(currency, payment_date DESC);

-- configurations 表索引
CREATE INDEX IF NOT EXISTS idx_configurations_key ON configurations(config_key);

-- notification_logs 表索引
CREATE INDEX IF NOT EXISTS idx_notification_logs_status ON notification_logs(status);
CREATE INDEX IF NOT EXISTS idx_notification_logs_created_at ON notification_logs(created_at DESC);

-- 創建更新時間觸發器函數
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 為需要的表添加自動更新 updated_at 觸發器
CREATE TRIGGER update_daily_earnings_updated_at BEFORE UPDATE ON daily_earnings 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_active_positions_updated_at BEFORE UPDATE ON active_positions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_lending_orders_updated_at BEFORE UPDATE ON lending_orders 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_configurations_updated_at BEFORE UPDATE ON configurations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 插入默認配置
INSERT INTO configurations (config_key, config_value, description) VALUES
    ('system.version', '"1.0.0"', 'System version'),
    ('system.maintenance_mode', 'false', 'Maintenance mode flag'),
    ('daily_settlement.enabled', 'true', 'Daily settlement process enabled'),
    ('daily_settlement.time', '"00:05"', 'Daily settlement execution time'),
    ('notifications.telegram.enabled', 'true', 'Telegram notifications enabled'),
    ('notifications.email.enabled', 'false', 'Email notifications enabled')
ON CONFLICT (config_key) DO NOTHING;

-- 創建視圖用於快速查詢
CREATE OR REPLACE VIEW daily_earnings_summary AS
SELECT 
    date,
    currency,
    total_interest,
    daily_return_rate,
    annualized_return,
    utilization_rate,
    primary_strategy,
    settlement_status,
    LAG(total_interest) OVER (PARTITION BY currency ORDER BY date) as prev_day_interest,
    (total_interest - LAG(total_interest) OVER (PARTITION BY currency ORDER BY date)) as daily_change
FROM daily_earnings
ORDER BY date DESC, currency;

-- 創建月度彙總視圖
CREATE OR REPLACE VIEW monthly_earnings_summary AS
SELECT 
    EXTRACT(YEAR FROM date) as year,
    EXTRACT(MONTH FROM date) as month,
    currency,
    SUM(total_interest) as total_monthly_interest,
    AVG(daily_return_rate) as avg_daily_return,
    AVG(utilization_rate) as avg_utilization_rate,
    COUNT(*) as trading_days,
    MAX(total_interest) as best_day_interest,
    MIN(total_interest) as worst_day_interest
FROM daily_earnings
WHERE settlement_status = 'COMPLETED'
GROUP BY EXTRACT(YEAR FROM date), EXTRACT(MONTH FROM date), currency
ORDER BY year DESC, month DESC, currency;

-- 權限設置
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bitfinex_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO bitfinex_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO bitfinex_user;

-- 完成初始化
INSERT INTO notification_logs (message_type, recipient, message, status, sent_at) VALUES
    ('system', 'admin', 'Database initialization completed successfully', 'SENT', CURRENT_TIMESTAMP);

ANALYZE;