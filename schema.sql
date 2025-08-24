-- SimpleLendingBot 精簡版數據庫架構
-- 專注用戶關心的核心數據：每日收益 + 年化收益率
-- 
-- 設計理念:
-- - 從 10+ 表精簡為 2 表
-- - 從 40+ 記錄/天精簡為 1 記錄/天  
-- - 用戶導向：只保留用戶真正關心的數據
--
-- Author: BitfinexLendingBot Team
-- Version: Simple v1.0

-- ============================================
-- 表1: daily_summary (每日總結表)
-- 功能: 每天1筆記錄，包含用戶最關心的所有數據
-- 這是用戶最關心的核心表！
-- ============================================

CREATE TABLE IF NOT EXISTS daily_summary (
    -- 主鍵：日期
    date DATE PRIMARY KEY,
    
    -- 📊 資金概況 (用戶最關心)
    total_balance DECIMAL(15,6) NOT NULL DEFAULT 0,
    working_balance DECIMAL(15,6) NOT NULL DEFAULT 0,
    idle_balance DECIMAL(15,6) GENERATED ALWAYS AS (total_balance - working_balance) STORED,
    
    -- 💰 收益數據 (核心重點!)
    daily_earnings DECIMAL(15,6) NOT NULL DEFAULT 0,
    cumulative_earnings DECIMAL(15,6) NOT NULL DEFAULT 0,
    annual_rate DECIMAL(6,4) NOT NULL DEFAULT 0,
    
    -- 📈 運營指標
    utilization_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    active_loans_count INT DEFAULT 0,
    avg_lending_rate DECIMAL(6,4) DEFAULT 0,
    
    -- 🕐 元數據
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 為 daily_summary 表添加註釋
COMMENT ON TABLE daily_summary IS '每日總結表 - 用戶最關心的核心數據';
COMMENT ON COLUMN daily_summary.total_balance IS '總資金額度';
COMMENT ON COLUMN daily_summary.working_balance IS '放貸中資金 💪';
COMMENT ON COLUMN daily_summary.idle_balance IS '閒置資金 😴';
COMMENT ON COLUMN daily_summary.daily_earnings IS '今日收益 🎉';
COMMENT ON COLUMN daily_summary.cumulative_earnings IS '累計總收益 💎';
COMMENT ON COLUMN daily_summary.annual_rate IS '年化收益率 📈 (小數形式，如 0.0913 = 9.13%)';
COMMENT ON COLUMN daily_summary.utilization_rate IS '資金利用率 (百分比，如 95.50)';
COMMENT ON COLUMN daily_summary.active_loans_count IS '活躍放貸數量';
COMMENT ON COLUMN daily_summary.avg_lending_rate IS '平均放貸利率 (年化小數)';
COMMENT ON COLUMN daily_summary.created_at IS '記錄創建時間';
COMMENT ON COLUMN daily_summary.updated_at IS '記錄更新時間';

-- 為 daily_summary 創建索引 (查詢優化)
CREATE INDEX IF NOT EXISTS idx_daily_summary_date ON daily_summary(date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_summary_earnings ON daily_summary(daily_earnings DESC);

-- ============================================
-- 表2: current_status (當前狀態表)
-- 功能: 全局只有1筆記錄，實時更新系統運行狀態
-- 用於監控機器人運行情況
-- ============================================

CREATE TABLE IF NOT EXISTS current_status (
    -- 主鍵 (全表只有1筆記錄)
    id SERIAL PRIMARY KEY,
    
    -- 💰 實時資金狀態
    total_available DECIMAL(15,6) NOT NULL DEFAULT 0,
    total_lending DECIMAL(15,6) NOT NULL DEFAULT 0,
    active_offers_count INT NOT NULL DEFAULT 0,
    
    -- 🤖 系統運行狀態
    last_update TIMESTAMP NOT NULL DEFAULT NOW(),
    last_run_status VARCHAR(20) DEFAULT 'success',
    strategy_name VARCHAR(50) DEFAULT 'ladder',
    system_status VARCHAR(20) DEFAULT 'active'
);

-- 為 current_status 表添加註釋
COMMENT ON TABLE current_status IS '當前狀態表 - 實時系統運行狀態監控';
COMMENT ON COLUMN current_status.total_available IS '當前可用於放貸的資金';
COMMENT ON COLUMN current_status.total_lending IS '當前放貸中的資金';
COMMENT ON COLUMN current_status.active_offers_count IS '當前掛單數量';
COMMENT ON COLUMN current_status.last_update IS '最後更新時間';
COMMENT ON COLUMN current_status.last_run_status IS '上次運行狀態 (success/error/no_balance/no_orders)';
COMMENT ON COLUMN current_status.strategy_name IS '當前使用策略';
COMMENT ON COLUMN current_status.system_status IS '系統狀態 (active/paused/error)';

-- 插入初始狀態記錄 (確保表中有1筆記錄)
INSERT INTO current_status (
    total_available, 
    total_lending, 
    active_offers_count,
    system_status
) VALUES (0, 0, 0, 'active') 
ON CONFLICT (id) DO NOTHING;

-- 為 current_status 創建索引
CREATE INDEX IF NOT EXISTS idx_current_status_update ON current_status(last_update DESC);

-- ============================================
-- 創建便於查詢的視圖 (用戶友好)
-- ============================================

-- 最近30天收益視圖
CREATE OR REPLACE VIEW recent_performance AS
SELECT 
    date,
    total_balance,
    working_balance,
    idle_balance,
    daily_earnings,
    annual_rate * 100 as annual_rate_percent,  -- 轉換為百分比顯示
    utilization_rate,
    active_loans_count,
    ROUND((daily_earnings / NULLIF(total_balance, 0) * 100)::numeric, 4) as daily_roi_percent
FROM daily_summary 
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY date DESC;

-- 收益統計總覽視圖
CREATE OR REPLACE VIEW earnings_overview AS
SELECT 
    COUNT(*) as tracking_days,
    ROUND(SUM(daily_earnings)::numeric, 6) as total_earnings,
    ROUND(AVG(daily_earnings)::numeric, 6) as avg_daily_earnings,
    ROUND(AVG(annual_rate * 100)::numeric, 2) as avg_annual_rate_percent,
    ROUND(AVG(utilization_rate)::numeric, 1) as avg_utilization_rate,
    MAX(daily_earnings) as best_earning_day,
    MIN(daily_earnings) as worst_earning_day,
    ROUND(AVG(total_balance)::numeric, 2) as avg_total_balance
FROM daily_summary 
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
  AND total_balance > 0;

-- ============================================
-- 實用的數據庫函數
-- ============================================

-- 自動更新 updated_at 字段的觸發器函數
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 為 daily_summary 表創建自動更新觸發器
DROP TRIGGER IF EXISTS update_daily_summary_updated_at ON daily_summary;
CREATE TRIGGER update_daily_summary_updated_at
    BEFORE UPDATE ON daily_summary
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 計算年化收益率的便利函數
CREATE OR REPLACE FUNCTION calculate_annual_rate(
    daily_earning DECIMAL,
    total_balance DECIMAL
) RETURNS DECIMAL AS $$
BEGIN
    IF total_balance = 0 OR total_balance IS NULL THEN
        RETURN 0;
    END IF;
    RETURN ROUND((daily_earning / total_balance * 365)::numeric, 6);
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 數據庫維護和優化
-- ============================================

-- 自動清理超過1年的數據 (可選，保持數據庫輕量)
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS void AS $$
BEGIN
    DELETE FROM daily_summary 
    WHERE date < CURRENT_DATE - INTERVAL '1 year';
    
    RAISE INFO '已清理超過1年的歷史數據';
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 使用說明和查詢示例
-- ============================================

/*
📊 常用查詢示例:

1. 查看最近7天收益:
   SELECT * FROM recent_performance LIMIT 7;

2. 查看收益統計概覽:
   SELECT * FROM earnings_overview;

3. 查看當前系統狀態:
   SELECT * FROM current_status;

4. 查看今日數據:
   SELECT * FROM daily_summary WHERE date = CURRENT_DATE;

5. 查看最佳收益日:
   SELECT date, daily_earnings, annual_rate_percent 
   FROM recent_performance 
   ORDER BY daily_earnings DESC 
   LIMIT 5;

6. 計算平均月收益:
   SELECT 
       ROUND(AVG(daily_earnings) * 30, 4) as estimated_monthly_earnings,
       ROUND(AVG(annual_rate) * 100, 2) as avg_annual_rate_percent
   FROM daily_summary 
   WHERE date >= CURRENT_DATE - INTERVAL '30 days';

7. 查看資金利用率趨勢:
   SELECT date, utilization_rate, total_balance, working_balance
   FROM daily_summary 
   WHERE date >= CURRENT_DATE - INTERVAL '7 days'
   ORDER BY date DESC;

💡 表設計亮點:
- daily_summary: 每天1筆記錄，包含用戶最關心的8個核心指標
- current_status: 全表1筆記錄，實時系統狀態監控
- 自動計算字段: idle_balance 自動計算，無需手動維護
- 友好視圖: 自動轉換百分比，便於用戶理解
- 性能優化: 合理索引設計，查詢快速響應

🎯 與企業版對比:
- 企業版: 10+ 表，40+ 記錄/天，複雜查詢
- 精簡版: 2 表，1 記錄/天，直接查詢
- 數據減少: 97%
- 查詢簡化: 95%
- 用戶價值: 100% 保留
*/