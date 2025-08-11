import logging
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal
from dataclasses import dataclass

from src.main.python.services.database_manager import DatabaseManager
from src.main.python.models.daily_earnings import (
    DailyEarnings, DailyEarningsCreate, DailyEarningsSummary,
    WeeklyEarningsSummary, MonthlyEarningsSummary, SettlementStatus
)
from src.main.python.core.exceptions import DatabaseError

log = logging.getLogger(__name__)


@dataclass
class EarningsFilter:
    """收益數據篩選器"""
    currency: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[SettlementStatus] = None


class DailyEarningsRepository:
    """每日收益數據倉庫"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def create_table(self):
        """創建每日收益表"""
        sql = """
        CREATE TABLE IF NOT EXISTS daily_earnings (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL,
            currency VARCHAR(6) NOT NULL,
            
            -- 用戶關心的核心數據
            total_interest NUMERIC(15,8) NOT NULL,
            deployed_amount NUMERIC(15,8) NOT NULL,
            available_amount NUMERIC(15,8) NOT NULL,
            weighted_avg_rate NUMERIC(10,8) NOT NULL,
            
            -- 效果指標
            utilization_rate NUMERIC(5,2) NOT NULL,
            daily_return_rate NUMERIC(10,8) NOT NULL,
            annualized_return NUMERIC(8,4) NOT NULL,
            
            -- 策略信息
            primary_strategy VARCHAR(20) NOT NULL,
            total_orders_placed INTEGER NOT NULL,
            orders_success_rate NUMERIC(5,2) NOT NULL,
            
            -- 市場環境
            market_avg_rate NUMERIC(10,8),
            market_competitiveness NUMERIC(5,2),
            
            -- 元數據
            settlement_status VARCHAR(20) DEFAULT 'PENDING',
            settlement_timestamp TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            
            UNIQUE(date, currency)
        );
        
        -- 創建索引
        CREATE INDEX IF NOT EXISTS idx_daily_earnings_date_currency 
        ON daily_earnings(date DESC, currency);
        
        CREATE INDEX IF NOT EXISTS idx_daily_earnings_status 
        ON daily_earnings(settlement_status);
        """
        
        try:
            self.db_manager.execute_query(sql)
            log.info("Daily earnings table created successfully")
        except Exception as e:
            log.error(f"Failed to create daily earnings table: {e}")
            raise DatabaseError(f"Table creation failed: {e}")
    
    def save(self, earnings: DailyEarningsCreate) -> DailyEarnings:
        """保存每日收益記錄"""
        sql = """
        INSERT INTO daily_earnings (
            date, currency, total_interest, deployed_amount, available_amount,
            weighted_avg_rate, utilization_rate, daily_return_rate, annualized_return,
            primary_strategy, total_orders_placed, orders_success_rate,
            market_avg_rate, market_competitiveness
        ) VALUES (
            %(date)s, %(currency)s, %(total_interest)s, %(deployed_amount)s, %(available_amount)s,
            %(weighted_avg_rate)s, %(utilization_rate)s, %(daily_return_rate)s, %(annualized_return)s,
            %(primary_strategy)s, %(total_orders_placed)s, %(orders_success_rate)s,
            %(market_avg_rate)s, %(market_competitiveness)s
        )
        ON CONFLICT (date, currency) 
        DO UPDATE SET
            total_interest = EXCLUDED.total_interest,
            deployed_amount = EXCLUDED.deployed_amount,
            available_amount = EXCLUDED.available_amount,
            weighted_avg_rate = EXCLUDED.weighted_avg_rate,
            utilization_rate = EXCLUDED.utilization_rate,
            daily_return_rate = EXCLUDED.daily_return_rate,
            annualized_return = EXCLUDED.annualized_return,
            primary_strategy = EXCLUDED.primary_strategy,
            total_orders_placed = EXCLUDED.total_orders_placed,
            orders_success_rate = EXCLUDED.orders_success_rate,
            market_avg_rate = EXCLUDED.market_avg_rate,
            market_competitiveness = EXCLUDED.market_competitiveness,
            settlement_status = 'PENDING'
        RETURNING *;
        """
        
        try:
            result = self.db_manager.execute_query(sql, earnings.dict())
            if result:
                row = result[0]
                return DailyEarnings(**row)
            else:
                raise DatabaseError("Failed to save daily earnings")
                
        except Exception as e:
            log.error(f"Failed to save daily earnings: {e}")
            raise DatabaseError(f"Save operation failed: {e}")
    
    def get_by_date(self, date: date, currency: str) -> Optional[DailyEarnings]:
        """根據日期獲取收益記錄"""
        sql = """
        SELECT * FROM daily_earnings 
        WHERE date = %(date)s AND currency = %(currency)s
        """
        
        try:
            result = self.db_manager.execute_query(sql, {'date': date, 'currency': currency})
            if result:
                return DailyEarnings(**result[0])
            return None
            
        except Exception as e:
            log.error(f"Failed to get daily earnings by date: {e}")
            raise DatabaseError(f"Query failed: {e}")
    
    def get_recent_earnings(self, currency: str, days: int = 30) -> List[DailyEarnings]:
        """獲取最近N天的收益記錄"""
        sql = """
        SELECT * FROM daily_earnings 
        WHERE currency = %(currency)s 
        AND date >= %(start_date)s
        ORDER BY date DESC
        LIMIT %(limit)s
        """
        
        start_date = date.today() - timedelta(days=days)
        params = {
            'currency': currency,
            'start_date': start_date,
            'limit': days
        }
        
        try:
            result = self.db_manager.execute_query(sql, params)
            return [DailyEarnings(**row) for row in result]
            
        except Exception as e:
            log.error(f"Failed to get recent earnings: {e}")
            raise DatabaseError(f"Query failed: {e}")
    
    def get_earnings_summary(self, currency: str, target_date: date) -> Optional[DailyEarningsSummary]:
        """獲取帶趨勢對比的收益摘要"""
        sql = """
        WITH target_earning AS (
            SELECT * FROM daily_earnings 
            WHERE date = %(target_date)s AND currency = %(currency)s
        ),
        comparisons AS (
            SELECT 
                'yesterday' as period,
                daily_return_rate as rate
            FROM daily_earnings 
            WHERE date = %(target_date)s - INTERVAL '1 day' AND currency = %(currency)s
            
            UNION ALL
            
            SELECT 
                'last_week' as period,
                daily_return_rate as rate
            FROM daily_earnings 
            WHERE date = %(target_date)s - INTERVAL '7 days' AND currency = %(currency)s
            
            UNION ALL
            
            SELECT 
                'last_month' as period,
                daily_return_rate as rate
            FROM daily_earnings 
            WHERE date = %(target_date)s - INTERVAL '30 days' AND currency = %(currency)s
        )
        SELECT 
            te.*,
            MAX(CASE WHEN c.period = 'yesterday' THEN te.daily_return_rate - c.rate END) as vs_yesterday,
            MAX(CASE WHEN c.period = 'last_week' THEN te.daily_return_rate - c.rate END) as vs_last_week,
            MAX(CASE WHEN c.period = 'last_month' THEN te.daily_return_rate - c.rate END) as vs_last_month
        FROM target_earning te
        LEFT JOIN comparisons c ON true
        GROUP BY te.id, te.date, te.currency, te.total_interest, te.daily_return_rate, 
                 te.annualized_return, te.utilization_rate, te.market_competitiveness
        """
        
        try:
            result = self.db_manager.execute_query(sql, {
                'target_date': target_date,
                'currency': currency
            })
            
            if result:
                row = result[0]
                return DailyEarningsSummary(
                    date=row['date'],
                    currency=row['currency'],
                    total_interest=row['total_interest'],
                    daily_return_rate=row['daily_return_rate'],
                    annualized_return=row['annualized_return'],
                    utilization_rate=row['utilization_rate'],
                    market_competitiveness=row['market_competitiveness'],
                    vs_yesterday=row['vs_yesterday'],
                    vs_last_week=row['vs_last_week'],
                    vs_last_month=row['vs_last_month']
                )
            return None
            
        except Exception as e:
            log.error(f"Failed to get earnings summary: {e}")
            raise DatabaseError(f"Query failed: {e}")
    
    def update_settlement_status(self, date: date, currency: str, 
                                status: SettlementStatus) -> bool:
        """更新結算狀態"""
        sql = """
        UPDATE daily_earnings 
        SET settlement_status = %(status)s,
            settlement_timestamp = CASE 
                WHEN %(status)s = 'COMPLETED' THEN NOW() 
                ELSE settlement_timestamp 
            END
        WHERE date = %(date)s AND currency = %(currency)s
        RETURNING id
        """
        
        try:
            result = self.db_manager.execute_query(sql, {
                'date': date,
                'currency': currency,
                'status': status.value
            })
            return len(result) > 0
            
        except Exception as e:
            log.error(f"Failed to update settlement status: {e}")
            raise DatabaseError(f"Update failed: {e}")
    
    def get_weekly_summary(self, currency: str, week_start: date) -> Optional[WeeklyEarningsSummary]:
        """獲取週收益摘要"""
        week_end = week_start + timedelta(days=6)
        sql = """
        SELECT 
            %(week_start)s as week_start,
            %(week_end)s as week_end,
            currency,
            SUM(total_interest) as total_interest,
            AVG(daily_return_rate) as avg_daily_return,
            AVG(utilization_rate) as avg_utilization_rate,
            SUM(total_orders_placed) as total_orders,
            (SELECT date FROM daily_earnings de2 
             WHERE de2.currency = de.currency 
             AND de2.date BETWEEN %(week_start)s AND %(week_end)s
             ORDER BY de2.daily_return_rate DESC LIMIT 1) as best_day,
            MAX(daily_return_rate) as best_day_return
        FROM daily_earnings de
        WHERE currency = %(currency)s 
        AND date BETWEEN %(week_start)s AND %(week_end)s
        GROUP BY currency
        """
        
        try:
            result = self.db_manager.execute_query(sql, {
                'currency': currency,
                'week_start': week_start,
                'week_end': week_end
            })
            
            if result:
                row = result[0]
                return WeeklyEarningsSummary(**row)
            return None
            
        except Exception as e:
            log.error(f"Failed to get weekly summary: {e}")
            raise DatabaseError(f"Query failed: {e}")
    
    def get_monthly_summary(self, currency: str, year: int, month: int) -> Optional[MonthlyEarningsSummary]:
        """獲取月收益摘要"""
        sql = """
        WITH monthly_data AS (
            SELECT *,
                ROW_NUMBER() OVER (ORDER BY daily_return_rate DESC) as rank_desc,
                ROW_NUMBER() OVER (ORDER BY daily_return_rate ASC) as rank_asc
            FROM daily_earnings 
            WHERE currency = %(currency)s 
            AND EXTRACT(YEAR FROM date) = %(year)s 
            AND EXTRACT(MONTH FROM date) = %(month)s
        ),
        strategy_performance AS (
            SELECT 
                primary_strategy,
                SUM(total_interest) as strategy_total,
                ROW_NUMBER() OVER (ORDER BY SUM(total_interest) DESC) as strategy_rank
            FROM monthly_data
            GROUP BY primary_strategy
        )
        SELECT 
            %(month)s as month,
            %(year)s as year,
            md.currency,
            SUM(md.total_interest) as total_interest,
            AVG(md.daily_return_rate) as avg_daily_return,
            AVG(md.utilization_rate) as avg_utilization_rate,
            SUM(md.total_orders_placed) as total_orders,
            (SELECT primary_strategy FROM strategy_performance WHERE strategy_rank = 1) as best_strategy,
            MIN(CASE WHEN md.rank_asc = 1 THEN md.date END) as worst_day,
            MAX(CASE WHEN md.rank_desc = 1 THEN md.date END) as best_day
        FROM monthly_data md
        GROUP BY md.currency
        """
        
        try:
            result = self.db_manager.execute_query(sql, {
                'currency': currency,
                'year': year,
                'month': month
            })
            
            if result:
                row = result[0]
                return MonthlyEarningsSummary(**row)
            return None
            
        except Exception as e:
            log.error(f"Failed to get monthly summary: {e}")
            raise DatabaseError(f"Query failed: {e}")