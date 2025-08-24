#!/usr/bin/env python3
"""
SimpleLendingBot - 極簡版放貸機器人

🎯 專注核心功能：
- 自動放貸 (階梯策略)
- 每日收益統計
- 成本最低 ($0/月)
- Railway 雲端部署

📊 用戶關心的數據：
- 每日收益 💰
- 年化收益率 📈
- 資金利用率
- 工作資金狀態

Author: BitfinexLendingBot Team
Version: Simple v1.0
"""

import os
import sys
import time
import logging
import schedule
import requests
import psycopg
import hmac
import hashlib
from datetime import datetime, date, timedelta
from decimal import Decimal
from decouple import config
from typing import Dict, List, Optional

# 簡化模塊：API + 階梯策略 (策略內部封裝市場數據)
from bitfinex_api import BitfinexAPI
from simple_ladder_strategy import SimpleLadderStrategy

# 配置日誌系統
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class SimpleDatabase:
    """精簡版數據庫管理 - 只處理 2 張核心表"""
    
    def __init__(self):
        self.db_url = config('DATABASE_URL')
        if not self.db_url:
            raise ValueError("數據庫連接字符串未配置，請設置 DATABASE_URL")
        
        # 測試數據庫連接
        self._test_connection()
        logger.info("數據庫連接成功")
    
    def _test_connection(self):
        """測試數據庫連接"""
        try:
            with psycopg.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT 1')
        except Exception as e:
            logger.error(f"數據庫連接失敗: {e}")
            raise
    
    def get_connection(self):
        """獲取數據庫連接"""
        return psycopg.connect(self.db_url)
    
    def initialize_tables(self):
        """初始化數據庫表結構"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # 創建 daily_summary 表
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS daily_summary (
                            date DATE PRIMARY KEY,
                            total_balance DECIMAL(15,6) NOT NULL DEFAULT 0,
                            working_balance DECIMAL(15,6) NOT NULL DEFAULT 0,
                            idle_balance DECIMAL(15,6) GENERATED ALWAYS AS (total_balance - working_balance) STORED,
                            daily_earnings DECIMAL(15,6) NOT NULL DEFAULT 0,
                            cumulative_earnings DECIMAL(15,6) NOT NULL DEFAULT 0,
                            annual_rate DECIMAL(6,4) NOT NULL DEFAULT 0,
                            utilization_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
                            active_loans_count INT DEFAULT 0,
                            avg_lending_rate DECIMAL(6,4) DEFAULT 0,
                            created_at TIMESTAMP DEFAULT NOW(),
                            updated_at TIMESTAMP DEFAULT NOW()
                        )
                    """)
                    
                    # 創建 current_status 表
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS current_status (
                            id SERIAL PRIMARY KEY,
                            total_available DECIMAL(15,6) NOT NULL DEFAULT 0,
                            total_lending DECIMAL(15,6) NOT NULL DEFAULT 0,
                            active_offers_count INT NOT NULL DEFAULT 0,
                            last_update TIMESTAMP NOT NULL DEFAULT NOW(),
                            last_run_status VARCHAR(20) DEFAULT 'success',
                            strategy_name VARCHAR(50) DEFAULT 'ladder',
                            system_status VARCHAR(20) DEFAULT 'active'
                        )
                    """)
                    
                    # 插入初始狀態記錄
                    cur.execute("""
                        INSERT INTO current_status (total_available, total_lending, active_offers_count) 
                        VALUES (0, 0, 0) 
                        ON CONFLICT (id) DO NOTHING
                    """)
                    
                    # 創建索引
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_daily_summary_date ON daily_summary(date DESC)")
                    
                    conn.commit()
                    logger.info("數據庫表初始化完成")
                    
        except Exception as e:
            logger.error(f"初始化數據庫表失敗: {e}")
            raise
    
    def update_daily_summary(self, data: Dict):
        """更新每日總結數據"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    sql = """
                        INSERT INTO daily_summary 
                        (date, total_balance, working_balance, daily_earnings, cumulative_earnings, 
                         annual_rate, utilization_rate, active_loans_count, avg_lending_rate)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (date) DO UPDATE SET
                            total_balance = EXCLUDED.total_balance,
                            working_balance = EXCLUDED.working_balance,
                            daily_earnings = EXCLUDED.daily_earnings,
                            cumulative_earnings = EXCLUDED.cumulative_earnings,
                            annual_rate = EXCLUDED.annual_rate,
                            utilization_rate = EXCLUDED.utilization_rate,
                            active_loans_count = EXCLUDED.active_loans_count,
                            avg_lending_rate = EXCLUDED.avg_lending_rate,
                            updated_at = NOW()
                    """
                    cur.execute(sql, (
                        data['date'], data['total_balance'], data['working_balance'],
                        data['daily_earnings'], data.get('cumulative_earnings', 0),
                        data['annual_rate'], data['utilization_rate'],
                        data['active_loans_count'], data['avg_lending_rate']
                    ))
                    conn.commit()
                    logger.info(f"每日總結已更新: {data['date']}")
        except Exception as e:
            logger.error(f"更新每日總結失敗: {e}")
    
    def update_current_status(self, data: Dict):
        """更新當前狀態"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    sql = """
                        UPDATE current_status SET
                            total_available = %s,
                            total_lending = %s,
                            active_offers_count = %s,
                            last_update = %s,
                            last_run_status = %s,
                            strategy_name = %s,
                            system_status = %s
                        WHERE id = 1
                    """
                    cur.execute(sql, (
                        data['total_available'], data['total_lending'],
                        data['active_offers_count'], data['last_update'],
                        data['last_run_status'], data['strategy_name'], 
                        data.get('system_status', 'active')
                    ))
                    conn.commit()
                    logger.info("當前狀態已更新")
        except Exception as e:
            logger.error(f"更新當前狀態失敗: {e}")
    
    def get_yesterday_summary(self) -> Optional[Dict]:
        """獲取昨日總結 (用於計算收益)"""
        try:
            yesterday = date.today() - timedelta(days=1)
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT total_balance, cumulative_earnings 
                        FROM daily_summary 
                        WHERE date = %s
                    """, (yesterday,))
                    result = cur.fetchone()
                    if result:
                        return {
                            'total_balance': result[0],
                            'cumulative_earnings': result[1]
                        }
            return None
        except Exception as e:
            logger.error(f"獲取昨日總結失敗: {e}")
            return None

class SimpleLendingBot:
    """極簡版放貸機器人 - 專注核心功能"""
    
    def __init__(self):
        logger.info("🚀 SimpleLendingBot 初始化開始...")
        
        # API 客戶端
        self.api = BitfinexAPI()
        
        # 數據庫管理
        self.db = SimpleDatabase()
        self.db.initialize_tables()
        
        # 基本配置參數
        self.currency = config('LENDING_CURRENCY', default='UST')
        self.min_amount = Decimal(config('MIN_ORDER_AMOUNT', default='150'))
        self.max_amount = Decimal(config('MAX_LOAN_AMOUNT', default='10000'))
        self.run_interval = int(config('RUN_INTERVAL_MINUTES', default='30'))
        
        # 放貸期限控制 (必需配置)
        self.min_period = int(config('LENDING_MIN_PERIOD', default='2'))
        self.max_period = int(config('LENDING_MAX_PERIOD', default='30'))
        self.preferred_period = int(config('LENDING_PREFERRED_PERIOD', default='7'))
        
        # 利率邊界保護 (必需配置)
        self.min_annual_rate = Decimal(config('MIN_ANNUAL_RATE', default='0.05'))
        self.max_annual_rate = Decimal(config('MAX_ANNUAL_RATE', default='0.50'))
        self.target_annual_rate = Decimal(config('TARGET_ANNUAL_RATE', default='0.12'))
        
        # 資金安全保護 (必需配置)
        self.max_utilization_rate = Decimal(config('MAX_UTILIZATION_RATE', default='100'))
        self.single_order_max_percent = Decimal(config('SINGLE_ORDER_MAX_PERCENT', default='25'))
        
        # 穩定性保障 (必需配置)
        self.max_retry_attempts = int(config('MAX_RETRY_ATTEMPTS', default='3'))
        self.retry_delay_seconds = int(config('RETRY_DELAY_SECONDS', default='5'))
        self.order_timeout_seconds = int(config('ORDER_TIMEOUT_SECONDS', default='30'))
        
        # Telegram 配置 (可選)
        self.telegram_token = config('TELEGRAM_BOT_TOKEN', default='')
        self.telegram_chat_id = config('TELEGRAM_CHAT_ID', default='')
        
        # 動態利率配置 (新增)
        enable_dynamic_str = config('ENABLE_DYNAMIC_RATE', default='false').lower()
        self.enable_dynamic_rate = enable_dynamic_str in ('true', '1', 'yes', 'on')
        self.market_rate_buffer_percent = int(config('MARKET_RATE_BUFFER_PERCENT', default='5'))
        self.min_rate_safety_margin = Decimal(config('MIN_RATE_SAFETY_MARGIN', default='0.02'))  # 2%
        
        # 初始化動態利率組件 (如果啟用)
        if self.enable_dynamic_rate:
            logger.info("🔥 動態階梯策略已啟用")
            
            # 創建簡單階梯策略配置
            class StrategyConfig:
                def __init__(self, buffer_pct, ladder_levels):
                    self.competitive_buffer_percent = buffer_pct
                    self.ladder_levels = ladder_levels
                    self.min_rate_threshold = 0.05  # 5% 年化最低門檻
            
            strategy_config = StrategyConfig(self.market_rate_buffer_percent, 10)
            # 傳入API客戶端，讓策略內部處理市場數據
            self.ladder_strategy = SimpleLadderStrategy(strategy_config, api_client=self.api)
        else:
            logger.info("📊 使用固定利率策略")
            self.ladder_strategy = None
        
        logger.info(f"✅ 配置加載完成:")
        logger.info(f"   💰 放貸幣種: {self.currency}")
        logger.info(f"   💵 訂單範圍: {self.min_amount} - {self.max_amount}")
        logger.info(f"   📅 放貸期限: {self.min_period}-{self.max_period}天 (首選{self.preferred_period}天)")
        logger.info(f"   📈 利率範圍: {float(self.min_annual_rate)*100:.1f}%-{float(self.max_annual_rate)*100:.1f}% (目標{float(self.target_annual_rate)*100:.1f}%)")
        logger.info(f"   ⚖️ 資金利用率: 最大{float(self.max_utilization_rate):.0f}% (單筆≤{float(self.single_order_max_percent):.0f}%)")
        logger.info(f"   🔄 重試設定: 最多{self.max_retry_attempts}次，間隔{self.retry_delay_seconds}秒")
        logger.info(f"   ⏰ 運行間隔: {self.run_interval} 分鐘")
        logger.info(f"   📱 Telegram: {'已配置' if self.telegram_token else '未配置'}")
        
        if self.enable_dynamic_rate:
            logger.info(f"   🔥 動態利率: 啟用 (緩衝{self.market_rate_buffer_percent}%, 安全邊際{float(self.min_rate_safety_margin)*100:.1f}%)")
        else:
            logger.info(f"   📊 利率策略: 固定利率")
    
    def send_telegram_notification(self, message: str):
        """發送 Telegram 通知"""
        if not self.telegram_token or not self.telegram_chat_id:
            return
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                logger.info("Telegram 通知發送成功")
            else:
                logger.warning(f"Telegram 通知發送失敗: {response.status_code}")
                
        except Exception as e:
            logger.error(f"發送 Telegram 通知失敗: {e}")
    
    
    def _calculate_optimal_ladder_count(self, usable_balance: Decimal) -> int:
        """
        動態計算最佳階梯檔數
        確保每筆訂單都不低於 min_amount
        
        Args:
            usable_balance: 實際可用餘額 (已扣除利用率限制)
            
        Returns:
            int: 最佳階梯檔數 (1-10)
        """
        # 理論最大檔數 (預設10檔)
        max_levels = 10
        
        # 考慮單筆訂單限制
        max_single_order = usable_balance * (self.single_order_max_percent / Decimal('100'))
        
        # 從最大檔數開始向下調整
        for levels in range(max_levels, 0, -1):
            # 平均每檔金額
            avg_amount_per_level = usable_balance / levels
            
            # 檢查是否滿足最小金額要求
            if avg_amount_per_level >= self.min_amount:
                # 檢查是否超過單筆限制
                if avg_amount_per_level <= max_single_order:
                    # 完美匹配：滿足最小金額且不超過單筆限制
                    logger.info(f"💡 動態調整階梯檔數: {levels}檔 (每檔約 {avg_amount_per_level:.2f}, 範圍: {self.min_amount}-{max_single_order})")
                    return levels
                else:
                    # 超過單筆限制，但仍滿足最小金額
                    # 檢查是否可以通過增加檔數來解決
                    min_levels_for_single_limit = int(usable_balance / max_single_order) + 1
                    
                    # 檢查增加檔數後是否還能滿足最小金額
                    if min_levels_for_single_limit <= max_levels:
                        avg_with_more_levels = usable_balance / min_levels_for_single_limit
                        if avg_with_more_levels >= self.min_amount:
                            # 可以通過增加檔數解決
                            logger.info(f"💡 基於單筆限制調整檔數: {min_levels_for_single_limit}檔 (每檔約 {avg_with_more_levels:.2f})")
                            return min_levels_for_single_limit
                    
                    # 無法通過增加檔數解決，優先滿足最小金額要求
                    logger.warning(f"⚠️  單筆限制沖突：選擇 {levels}檔 (每檔{avg_amount_per_level:.2f} > 單筆限制{max_single_order:.2f}，但滿足最小金額)")
                    return levels
        
        # 如果所有檔數都不滿足，返回1檔 (全部資金一筆)
        logger.warning(f"⚠️  無法滿足最小金額要求，使用1檔策略 (總金額: {usable_balance})")
        return 1
    
    
    def _generate_ladder_orders(self, available_balance: Decimal) -> List[Dict]:
        """
        使用 SimpleLadderStrategy 生成階梯訂單
        
        Args:
            available_balance: 可用餘額
            
        Returns:
            List[Dict]: 訂單列表
        """
        try:
            if self.ladder_strategy:
                # 計算可用餘額
                usable_balance = available_balance * (self.max_utilization_rate / Decimal('100'))
                
                # 計算最佳階梯檔數
                optimal_levels = self._calculate_optimal_ladder_count(usable_balance)
                
                # 使用 SimpleLadderStrategy 生成階梯利率
                strategy_result = self.ladder_strategy.generate_ladder_rates(
                    currency=self.currency,
                    target_levels=optimal_levels
                )
                
                if strategy_result and 'ladder_rates' in strategy_result:
                    ladder_rates = strategy_result['ladder_rates']
                    
                    # 轉換為主程序期望的格式
                    return self._convert_ladder_strategy_to_orders(available_balance, ladder_rates)
                else:
                    logger.warning("SimpleLadderStrategy 未返回有效階梯數據")
                    return []
            else:
                # 回退到固定利率策略
                return self._create_fixed_rate_orders(available_balance)
                
        except Exception as e:
            logger.error(f"生成階梯訂單失敗: {e}")
            return []
    
    def _convert_ladder_strategy_to_orders(self, available_balance: Decimal, ladder_rates: List[Dict]) -> List[Dict]:
        """
        將 SimpleLadderStrategy 的輸出轉換為主程序期望的訂單格式
        
        Args:
            available_balance: 可用餘額
            ladder_rates: SimpleLadderStrategy 返回的階梯利率列表
            
        Returns:
            List[Dict]: 訂單列表
        """
        # 計算可用餘額
        usable_balance = available_balance * (self.max_utilization_rate / Decimal('100'))
        max_single_order = usable_balance * (self.single_order_max_percent / Decimal('100'))
        
        orders = []
        total_amount = Decimal('0')
        actual_period = max(self.min_period, min(self.preferred_period, self.max_period))
        
        for ladder in ladder_rates:
            # 根據權重分配金額
            weight = Decimal(str(ladder['weight_suggestion']))
            amount = usable_balance * weight
            
            # 應用單筆訂單限制
            amount = min(amount, max_single_order)
            amount = round(amount, 2)  # 保留兩位小數
            
            if amount >= self.min_amount:
                # 使用階梯策略的日利率
                daily_rate = Decimal(str(ladder['daily_rate']))
                
                orders.append({
                    'amount': amount,
                    'rate': daily_rate,  # 日利率
                    'period': actual_period,
                    'annual_rate_pct': float(daily_rate * 365 * 100),  # 轉換為年化百分比
                    'level': ladder['level']
                })
                total_amount += amount
        
        logger.info(f"🎯 階梯策略生成:")
        logger.info(f"   📊 階梯數量: {len(orders)}")
        logger.info(f"   💰 可用餘額: {available_balance} → 實用餘額: {usable_balance} (利用率≤{self.max_utilization_rate}%)")
        logger.info(f"   💵 總分配: {total_amount} {self.currency} (單筆≤{max_single_order})")
        if orders:
            min_rate = min(order['annual_rate_pct'] for order in orders)
            max_rate = max(order['annual_rate_pct'] for order in orders)
            logger.info(f"   📈 利率範圍: {min_rate:.2f}% - {max_rate:.2f}% (年化)")
        logger.info(f"   📅 放貸期限: {actual_period}天")
        
        return orders
    
    def run_cycle(self):
        """主要運行週期 - 每30分鐘執行一次"""
        cycle_start = datetime.now()
        logger.info("=" * 50)
        logger.info(f"🔄 開始運行週期 - {cycle_start.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 50)
        
        try:
            # 1. 取消所有活躍訂單
            logger.info("1️⃣ 取消活躍訂單...")
            cancelled = self.api.cancel_all_funding_offers(self.currency)
            time.sleep(2)  # 等待取消生效
            
            # 2. 檢查所有錢包並自動轉移資金
            logger.info("2️⃣ 檢查錢包狀態...")
            all_wallets = self.api.get_all_wallet_balances()
            
            # 檢查 funding 錢包餘額
            funding_balance = all_wallets.get('funding', {}).get(self.currency, Decimal('0'))
            exchange_balance = all_wallets.get('exchange', {}).get(self.currency, Decimal('0'))
            
            logger.info(f"💰 funding 錢包: {funding_balance} {self.currency}")
            logger.info(f"💱 exchange 錢包: {exchange_balance} {self.currency}")
            
            # 如果 funding 錢包資金不足但 exchange 錢包有資金，自動轉移
            if funding_balance < self.min_amount and exchange_balance > 0:
                transfer_amount = exchange_balance
                logger.info(f"🔄 自動轉移 {transfer_amount} {self.currency} 從 exchange 到 funding 錢包...")
                
                if self.api.transfer_between_wallets(self.currency, transfer_amount, 'exchange', 'funding'):
                    time.sleep(2)  # 等待轉帳生效
                    # 重新獲取 funding 錢包餘額
                    balances = self.api.get_wallet_balances()
                    available = balances.get(self.currency, Decimal('0'))
                    logger.info(f"✅ 轉帳成功，funding 錢包現有: {available} {self.currency}")
                else:
                    logger.error("❌ 轉帳失敗")
                    available = funding_balance
            else:
                available = funding_balance
            
            if available <= 0:
                logger.warning("⚠️  沒有可用餘額，跳過本次運行")
                self._update_status(Decimal('0'), Decimal('0'), 0, 'no_balance')
                return
            
            logger.info(f"💰 可用於放貸的餘額: {available} {self.currency}")
            
            # 3. 探測實際可用放貸金額
            logger.info("3️⃣ 探測實際可用放貸金額...")
            actual_available = self._probe_available_lending_amount(available)
            logger.info(f"🔍 探測結果: 實際可用放貸金額 {actual_available} {self.currency}")
            
            if actual_available <= 0:
                logger.warning("⚠️  探測發現無可用放貸金額，跳過本次運行")
                self._update_status(available, Decimal('0'), 0, 'no_lending_balance')
                return
            
            # 4. 基於實際可用金額執行階梯策略
            logger.info("4️⃣ 執行階梯策略...")
            orders = self._generate_ladder_orders(actual_available)
            
            if not orders:
                logger.warning("⚠️  策略未生成訂單")
                self._update_status(available, Decimal('0'), 0, 'no_orders')
                return
            
            # 5. 提交訂單
            logger.info("5️⃣ 提交放貸訂單...")
            successful_orders = 0
            total_lending = Decimal('0')
            remaining_balance = actual_available  # 使用實際可用金額
            consecutive_failures = 0
            
            for i, order in enumerate(orders, 1):
                # 動態重新分配剩餘資金到剩餘訂單
                remaining_orders = len(orders) - i + 1
                if remaining_orders > 0 and remaining_balance > 0:
                    # 重新計算每筆訂單的平均金額
                    avg_amount_per_order = remaining_balance / remaining_orders
                    # 使用平均金額，但不超過原訂單金額和單筆限制
                    max_single_order = remaining_balance * (self.single_order_max_percent / Decimal('100'))
                    adjusted_amount = min(avg_amount_per_order, order['amount'], max_single_order)
                else:
                    adjusted_amount = min(order['amount'], remaining_balance)
                
                # 如果調整後的金額小於最小金額，跳過
                if adjusted_amount < self.min_amount:
                    logger.info(f"   跳過訂單 {i}/{len(orders)}: 調整後金額 {adjusted_amount:.2f} 小於最小金額 {self.min_amount}")
                    consecutive_failures += 1
                    if consecutive_failures >= 3:  # 連續3次失敗則停止
                        logger.warning("   連續失敗過多，停止提交剩餘訂單")
                        break
                    continue
                
                if adjusted_amount != order['amount']:
                    logger.info(f"   提交訂單 {i}/{len(orders)}: {adjusted_amount:.2f} {self.currency} @ {order['annual_rate_pct']:.4f}% (年化) [動態調整: 原{order['amount']:.2f} → 新{adjusted_amount:.2f}]")
                else:
                    logger.info(f"   提交訂單 {i}/{len(orders)}: {adjusted_amount:.2f} {self.currency} @ {order['annual_rate_pct']:.4f}% (年化)")
                
                result = self.api.submit_funding_offer(
                    self.currency,
                    adjusted_amount,
                    order['rate'],
                    order['period']
                )
                
                if result:
                    successful_orders += 1
                    total_lending += adjusted_amount
                    remaining_balance -= adjusted_amount
                    consecutive_failures = 0  # 重置失敗計數
                    time.sleep(1)  # 避免請求過快
                else:
                    consecutive_failures += 1
                    logger.warning(f"   訂單 {i} 提交失敗，剩餘資金: {remaining_balance}")
                    
                    # 如果連續失敗且剩餘資金很少，停止提交
                    if consecutive_failures >= 2 and remaining_balance < self.min_amount * 2:
                        logger.warning("   連續失敗且剩餘資金不足，停止提交剩餘訂單")
                        break
            
            # 6. 更新系統狀態
            logger.info("6️⃣ 更新系統狀態...")
            self._update_status(available, total_lending, successful_orders, 'success')
            
            # 7. 發送成功通知
            cycle_end = datetime.now()
            runtime = (cycle_end - cycle_start).total_seconds()
            
            # 計算利率範圍 
            rate_range_text = ""
            if orders:
                min_rate = min(order['annual_rate_pct'] for order in orders)
                max_rate = max(order['annual_rate_pct'] for order in orders)
                min_daily_rate = min_rate / 365
                max_daily_rate = max_rate / 365
                rate_range_text = f"📊 <b>日利率區間</b>: {min_daily_rate:.4f}% - {max_daily_rate:.4f}%\n"
            
            success_message = f"""
🤖 <b>SimpleLendingBot 運行報告</b>

⏰ <b>運行時間</b>: {cycle_start.strftime('%Y-%m-%d %H:%M:%S')}
💰 <b>可用餘額</b>: {available:,.2f} {self.currency}
📊 <b>成功訂單</b>: {successful_orders}/{len(orders)}
💵 <b>放貸金額</b>: {total_lending:,.2f} {self.currency}
📈 <b>資金利用率</b>: {(total_lending/available*100):.1f}%
{rate_range_text}
🎯 <b>策略</b>: 10階梯放貸
⚡ <b>執行時間</b>: {runtime:.1f} 秒
✅ <b>狀態</b>: 正常運行

下次運行: {self.run_interval} 分鐘後
            """.strip()
            
            self.send_telegram_notification(success_message)
            
            logger.info("✅ 運行週期完成")
            logger.info(f"   📊 成功: {successful_orders}/{len(orders)} 訂單")
            logger.info(f"   💰 金額: {total_lending} {self.currency}")
            logger.info(f"   ⚡ 耗時: {runtime:.1f} 秒")
            logger.info("=" * 50)
            
        except Exception as e:
            logger.error(f"❌ 運行週期出現錯誤: {e}")
            
            # 更新錯誤狀態
            self._update_status(Decimal('0'), Decimal('0'), 0, 'error')
            
            # 發送錯誤通知
            error_message = f"""
❌ <b>SimpleLendingBot 錯誤報告</b>

🕐 <b>發生時間</b>: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
⚠️ <b>錯誤信息</b>: {str(e)[:200]}...

請檢查系統狀態和日誌。
機器人將在下次週期重試。
            """.strip()
            
            self.send_telegram_notification(error_message)
    
    def _probe_available_lending_amount(self, wallet_balance: Decimal) -> Decimal:
        """
        探測實際可用的放貸金額
        通過二分法快速找到最大可用金額
        
        Args:
            wallet_balance: 錢包顯示的餘額
            
        Returns:
            Decimal: 實際可用於放貸的金額
        """
        try:
            # 使用固定的500 USD進行簡單測試
            test_amount = Decimal('500')
            actual_amount = Decimal('0')
            
            logger.info(f"🔍 使用固定 {test_amount} USD 進行探測測試")
            
            # 使用最低利率快速測試
            test_rate = self.min_annual_rate / 365  # 轉換為日利率
            
            # 提交測試訂單
            result = self.api.submit_funding_offer(
                self.currency,
                test_amount,
                test_rate,
                self.min_period
            )
            
            if result:
                logger.info(f"   ✅ {test_amount} USD 測試成功")
                
                # 立即取消測試訂單
                time.sleep(1)
                self.api.cancel_all_funding_offers(self.currency)
                
                # 基於500 USD測試推估總可用金額
                # 如果500 USD測試成功，估算總可用金額約為500的8-12倍（更保守）
                estimated_total = test_amount * 10  # 保守估計為10倍 (500 * 10 = 5000)
                # 但不能超過錢包餘額的25%
                max_safe_amount = wallet_balance * Decimal('0.25')
                actual_amount = min(estimated_total, max_safe_amount)
                logger.info(f"🎯 探測完成，基於 {test_amount} USD 測試成功，估算總可用: {actual_amount:.2f}")
                
            else:
                logger.warning(f"   ❌ {test_amount} USD 測試失敗")
                actual_amount = Decimal('0')
            
            return actual_amount
            
        except Exception as e:
            logger.error(f"探測可用放貸金額失敗: {e}")
            # 回退到保守估計
            return wallet_balance * Decimal('0.3')  # 使用30%作為保守估計
    
    def _update_status(self, available: Decimal, lending: Decimal, orders: int, status: str):
        """更新系統狀態"""
        try:
            status_data = {
                'total_available': available,
                'total_lending': lending,
                'active_offers_count': orders,
                'last_update': datetime.now(),
                'last_run_status': status,
                'strategy_name': 'ladder',
                'system_status': 'active'
            }
            self.db.update_current_status(status_data)
        except Exception as e:
            logger.error(f"更新系統狀態失敗: {e}")
    
    def daily_settlement(self):
        """每日結算 - 計算和記錄每日收益"""
        settlement_start = datetime.now()
        today = date.today()
        
        logger.info("🏦" * 20)
        logger.info(f"📊 開始每日結算 - {today}")
        logger.info("🏦" * 20)
        
        try:
            # 1. 獲取當前餘額
            logger.info("1️⃣ 獲取當前餘額...")
            balances = self.api.get_wallet_balances()
            total_balance = balances.get(self.currency, Decimal('0'))
            
            # 2. 獲取活躍放貸
            logger.info("2️⃣ 分析活躍放貸...")
            active_offers = self.api.get_active_funding_offers(self.currency)
            
            working_balance = Decimal('0')
            total_annual_rate = Decimal('0')
            valid_offers = 0
            
            for offer in active_offers:
                if len(offer) >= 5:
                    amount = Decimal(str(offer[2]))  # amount
                    rate = Decimal(str(offer[3]))    # rate (annual %)
                    
                    working_balance += amount
                    total_annual_rate += rate
                    valid_offers += 1
            
            avg_lending_rate = total_annual_rate / valid_offers if valid_offers > 0 else Decimal('0')
            utilization_rate = (working_balance / total_balance * 100) if total_balance > 0 else Decimal('0')
            
            # 3. 計算每日收益
            logger.info("3️⃣ 計算每日收益...")
            yesterday_data = self.db.get_yesterday_summary()
            
            daily_earnings = Decimal('0')
            cumulative_earnings = Decimal('0')
            annual_rate = Decimal('0')
            
            if yesterday_data and total_balance > 0:
                # 簡單計算：今日餘額 - 昨日餘額 = 收益 (忽略入金出金)
                balance_change = total_balance - yesterday_data['total_balance']
                if balance_change > 0:
                    daily_earnings = balance_change
                
                cumulative_earnings = yesterday_data['cumulative_earnings'] + daily_earnings
                annual_rate = (daily_earnings / total_balance * 365) if total_balance > 0 else Decimal('0')
            else:
                # 首次運行，使用預估值
                if working_balance > 0:
                    estimated_daily_rate = avg_lending_rate / 365 / 100
                    daily_earnings = working_balance * estimated_daily_rate
                    cumulative_earnings = daily_earnings
                    annual_rate = avg_lending_rate / 100
            
            # 4. 保存每日總結
            logger.info("4️⃣ 保存每日總結...")
            daily_data = {
                'date': today,
                'total_balance': total_balance,
                'working_balance': working_balance,
                'daily_earnings': daily_earnings,
                'cumulative_earnings': cumulative_earnings,
                'annual_rate': annual_rate,
                'utilization_rate': utilization_rate,
                'active_loans_count': valid_offers,
                'avg_lending_rate': avg_lending_rate / 100  # 轉為小數
            }
            
            self.db.update_daily_summary(daily_data)
            
            # 5. 發送每日報告
            settlement_end = datetime.now()
            runtime = (settlement_end - settlement_start).total_seconds()
            
            daily_report = f"""
📊 <b>每日收益報告</b> - {today.strftime('%Y-%m-%d')}

💰 <b>總資金</b>: {total_balance:,.2f} {self.currency}
💪 <b>工作資金</b>: {working_balance:,.2f} {self.currency} ({utilization_rate:.1f}%)
😴 <b>閒置資金</b>: {(total_balance-working_balance):,.2f} {self.currency}

🎉 <b>今日收益</b>: {daily_earnings:.4f} {self.currency}
📈 <b>年化收益率</b>: {annual_rate*100:.2f}%
💎 <b>累計收益</b>: {cumulative_earnings:.4f} {self.currency}

🎯 <b>放貸詳情</b>:
   📋 活躍放貸: {valid_offers} 筆
   📊 平均利率: {avg_lending_rate:.4f}% (年化)
   ⚡ 結算耗時: {runtime:.1f} 秒

✅ <b>每日結算完成</b>
            """.strip()
            
            self.send_telegram_notification(daily_report)
            
            logger.info("✅ 每日結算完成")
            logger.info(f"   💰 總資金: {total_balance}")
            logger.info(f"   🎉 今日收益: {daily_earnings}")
            logger.info(f"   📈 年化收益率: {annual_rate*100:.2f}%")
            logger.info("🏦" * 20)
            
        except Exception as e:
            logger.error(f"❌ 每日結算出現錯誤: {e}")
            
            error_message = f"""
❌ <b>每日結算錯誤</b>

🕐 <b>時間</b>: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
⚠️ <b>錯誤</b>: {str(e)[:200]}

請檢查系統狀態。
            """.strip()
            
            self.send_telegram_notification(error_message)
    
    def start(self):
        """啟動機器人"""
        logger.info("🚀" * 20)
        logger.info("🚀 SimpleLendingBot 正式啟動！")
        logger.info("🚀" * 20)
        
        # 發送啟動通知
        start_message = f"""
🚀 <b>SimpleLendingBot 已啟動</b>

💰 <b>放貸幣種</b>: {self.currency}
⏰ <b>運行間隔</b>: {self.run_interval} 分鐘
📊 <b>策略</b>: 10階梯放貸
💵 <b>訂單範圍</b>: {self.min_amount} - {self.max_amount}

🎯 <b>專注目標</b>:
   • 每日收益統計
   • 年化收益率計算  
   • 資金利用率優化
   • 成本最低運營 ($0/月)

系統開始自動運行...
        """.strip()
        
        self.send_telegram_notification(start_message)
        
        # 設置定時任務
        schedule.every(self.run_interval).minutes.do(self.run_cycle)
        schedule.every().day.at("00:05").do(self.daily_settlement)
        
        logger.info(f"⏰ 定時任務設置完成:")
        logger.info(f"   🔄 主循環: 每 {self.run_interval} 分鐘")
        logger.info(f"   📊 每日結算: 每天 00:05")
        
        # 立即執行一次主循環 (測試)
        logger.info("🧪 執行初始測試...")
        try:
            self.run_cycle()
        except Exception as e:
            logger.error(f"初始測試失敗: {e}")
        
        # 主事件循環
        logger.info("🔁 進入主事件循環...")
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分鐘檢查一次
            except KeyboardInterrupt:
                logger.info("👋 接收到停止信號...")
                break
            except Exception as e:
                logger.error(f"主循環錯誤: {e}")
                time.sleep(300)  # 錯誤時等待5分鐘
        
        # 發送停止通知
        stop_message = "⏹️ SimpleLendingBot 已停止運行"
        self.send_telegram_notification(stop_message)
        logger.info("👋 SimpleLendingBot 已安全關閉")

# Railway 健康檢查端點 (可選)
def health_check_server():
    """Railway 需要的健康檢查服務"""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import threading
    
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/health':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "healthy", "service": "SimpleLendingBot"}')
            else:
                self.send_response(404)
                self.end_headers()
    
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    
    def run_server():
        logger.info(f"健康檢查服務啟動於端口 {port}")
        server.serve_forever()
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()

if __name__ == "__main__":
    try:
        # 啟動健康檢查服務 (Railway 需要)
        health_check_server()
        
        # 啟動主機器人
        bot = SimpleLendingBot()
        bot.start()
        
    except KeyboardInterrupt:
        logger.info("👋 接收到終止信號，正在關閉...")
    except Exception as e:
        logger.error(f"💥 機器人啟動失敗: {e}")
        sys.exit(1)