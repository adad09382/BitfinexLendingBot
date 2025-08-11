-- Phase 1: 創建優化後的數據表結構
-- 目標：大幅簡化數據存儲，聚焦用戶關心的核心指標

-- 1. 帳戶狀態表 (每日一條記錄，替代複雜的訂單追蹤)
CREATE TABLE account_status_v2 (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    
    -- 資金分佈 (用戶最關心的數據)
    total_balance DECIMAL(15,2) NOT NULL,      -- 總資金
    lending_amount DECIMAL(15,2) NOT NULL,     -- 放貸中金額 (錢在工作)
    available_amount DECIMAL(15,2) NOT NULL,   -- 可用金額 (錢在閒置)
    utilization_rate DECIMAL(5,2) NOT NULL,    -- 資金利用率 %
    
    -- 每日收益 (核心價值指標)
    daily_interest DECIMAL(15,8) NOT NULL,     -- 當日利息收入
    cumulative_interest DECIMAL(15,8) NOT NULL, -- 累積利息收入
    
    -- 收益率指標 (用戶決策依據)
    daily_roi DECIMAL(8,4) NOT NULL,           -- 日收益率 %
    annualized_roi DECIMAL(8,4) NOT NULL,      -- 年化收益率 %
    
    -- 運營狀況
    active_orders_count INTEGER NOT NULL,      -- 活躍訂單數
    avg_lending_rate DECIMAL(8,4) NOT NULL,    -- 平均放貸利率
    
    -- 市場對比
    market_avg_rate DECIMAL(8,4),              -- 市場平均利率
    rate_competitiveness DECIMAL(8,4),         -- 利率競爭力 (我們-市場)
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 創建索引優化查詢
CREATE INDEX idx_account_status_v2_date ON account_status_v2(date);
CREATE INDEX idx_account_status_v2_roi ON account_status_v2(annualized_roi);

-- 2. 策略效果統計表 (簡化版，聚焦ROI對比)
CREATE TABLE strategy_performance_v2 (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    strategy_name VARCHAR(50) NOT NULL,
    
    -- 核心效果指標
    allocated_amount DECIMAL(15,2) NOT NULL,   -- 該策略分配金額
    daily_return DECIMAL(15,8) NOT NULL,       -- 當日收益
    roi_1d DECIMAL(8,4) NOT NULL,              -- 1日收益率
    roi_7d DECIMAL(8,4) NOT NULL,              -- 7日年化收益率  
    roi_30d DECIMAL(8,4) NOT NULL,             -- 30日年化收益率
    
    -- 效率指標
    utilization_rate DECIMAL(5,2) NOT NULL,    -- 該策略資金利用率
    avg_fill_rate DECIMAL(8,4) NOT NULL,       -- 平均成交利率
    orders_count INTEGER NOT NULL,             -- 訂單數量
    
    -- 風險指標
    volatility DECIMAL(8,4),                   -- 收益波動性
    max_drawdown DECIMAL(8,4),                 -- 最大回撤
    
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, strategy_name)
);

CREATE INDEX idx_strategy_performance_v2_date ON strategy_performance_v2(date);
CREATE INDEX idx_strategy_performance_v2_roi ON strategy_performance_v2(roi_30d);

-- 3. 每日運營概況表 (替代複雜的訂單明細追蹤)
CREATE TABLE daily_operations_v2 (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    
    -- 操作統計
    orders_placed INTEGER NOT NULL,            -- 當日下單數
    orders_filled INTEGER NOT NULL,            -- 當日成交數
    fill_rate DECIMAL(5,2) NOT NULL,           -- 成交率 %
    
    -- 資金流動
    total_amount_placed DECIMAL(15,2) NOT NULL, -- 下單總金額
    total_amount_filled DECIMAL(15,2) NOT NULL, -- 成交總金額
    
    -- 效率指標
    avg_order_size DECIMAL(15,2) NOT NULL,     -- 平均訂單大小
    optimal_order_size DECIMAL(15,2),          -- 當日最優訂單大小
    
    -- 市場情況
    market_avg_rate DECIMAL(8,4) NOT NULL,     -- 市場平均利率
    our_avg_rate DECIMAL(8,4) NOT NULL,        -- 我們的平均利率
    rate_advantage DECIMAL(8,4) NOT NULL,      -- 利率優勢
    
    -- 系統狀況  
    api_calls_count INTEGER NOT NULL,          -- API調用次數
    api_success_rate DECIMAL(5,2) NOT NULL,    -- API成功率
    system_uptime_minutes INTEGER NOT NULL,    -- 系統運行時間
    
    -- 改善建議數據
    potential_improvement JSONB,               -- 潛在改善空間
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_daily_operations_v2_date ON daily_operations_v2(date);

-- 4. 用戶關注指標快照表 (實時查詢優化)
CREATE TABLE user_dashboard_cache (
    id SERIAL PRIMARY KEY,
    cache_key VARCHAR(100) NOT NULL UNIQUE,    -- 緩存鍵
    cache_data JSONB NOT NULL,                  -- 緩存數據
    expires_at TIMESTAMP NOT NULL,             -- 過期時間
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_dashboard_cache_key ON user_dashboard_cache(cache_key);
CREATE INDEX idx_user_dashboard_cache_expires ON user_dashboard_cache(expires_at);

-- 5. 資金利用率優化建議表
CREATE TABLE optimization_suggestions (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    suggestion_type VARCHAR(50) NOT NULL,      -- 建議類型
    current_value DECIMAL(15,8) NOT NULL,      -- 當前值
    optimal_value DECIMAL(15,8) NOT NULL,      -- 最優值
    potential_gain DECIMAL(15,8) NOT NULL,     -- 潛在收益提升
    confidence_score DECIMAL(3,2) NOT NULL,    -- 建議可信度
    suggestion_text TEXT NOT NULL,             -- 建議描述
    implemented BOOLEAN DEFAULT FALSE,         -- 是否已實施
    implemented_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_optimization_suggestions_date ON optimization_suggestions(date);
CREATE INDEX idx_optimization_suggestions_type ON optimization_suggestions(suggestion_type);

-- 6. 創建視圖簡化查詢
CREATE VIEW user_performance_summary AS
SELECT 
    date,
    total_balance,
    lending_amount,
    utilization_rate,
    daily_interest,
    annualized_roi,
    rate_competitiveness,
    -- 計算改善潛力
    CASE 
        WHEN utilization_rate < 95 THEN 
            (100 - utilization_rate) * total_balance / 100 * annualized_roi / 365
        ELSE 0 
    END as potential_daily_gain
FROM account_status_v2
ORDER BY date DESC;

CREATE VIEW strategy_comparison AS
SELECT 
    s.strategy_name,
    s.roi_30d,
    s.allocated_amount,
    s.utilization_rate,
    s.volatility,
    -- 計算策略效率評分
    (s.roi_30d * 0.4 + s.utilization_rate * 0.3 + (100 - s.volatility * 100) * 0.3) as efficiency_score
FROM strategy_performance_v2 s
WHERE s.date = CURRENT_DATE - INTERVAL '1 day'
ORDER BY efficiency_score DESC;

-- 7. 創建數據清理函數
CREATE OR REPLACE FUNCTION cleanup_optimized_data() RETURNS void AS $$
BEGIN
    -- 保留6個月的詳細數據
    DELETE FROM account_status_v2 WHERE date < CURRENT_DATE - INTERVAL '6 months';
    DELETE FROM strategy_performance_v2 WHERE date < CURRENT_DATE - INTERVAL '6 months';
    DELETE FROM daily_operations_v2 WHERE date < CURRENT_DATE - INTERVAL '6 months';
    
    -- 清理過期緩存
    DELETE FROM user_dashboard_cache WHERE expires_at < NOW();
    
    -- 清理已實施的舊建議
    DELETE FROM optimization_suggestions 
    WHERE implemented = TRUE AND implemented_at < CURRENT_DATE - INTERVAL '30 days';
    
    RAISE NOTICE '優化數據清理完成';
END;
$$ LANGUAGE plpgsql;

-- 8. 權限設置
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bitfinex_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO bitfinex_user;

COMMIT;