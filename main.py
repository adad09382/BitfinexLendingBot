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
import psycopg2
import hmac
import hashlib
from datetime import datetime, date, timedelta
from decimal import Decimal
from decouple import config
from typing import Dict, List, Optional

# 配置日誌系統
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class SimpleBitfinexAPI:
    """精簡版 Bitfinex API 客戶端 - 只包含核心功能"""
    
    def __init__(self):
        self.api_key = config('BITFINEX_API_KEY')
        self.api_secret = config('BITFINEX_API_SECRET')
        self.base_url = 'https://api.bitfinex.com'
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # 驗證 API 配置
        if not self.api_key or not self.api_secret:
            raise ValueError("Bitfinex API 密鑰未配置，請檢查 .env 文件")
            
        logger.info("Bitfinex API 客戶端初始化完成")
    
    def _generate_auth_headers(self, path: str, body: str = '') -> Dict[str, str]:
        """生成 Bitfinex API 認證頭"""
        nonce = str(int(time.time() * 1000))
        signature_payload = f'/api/{path}{nonce}{body}'
        
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_payload.encode('utf-8'),
            hashlib.sha384
        ).hexdigest()
        
        return {
            'bfx-nonce': nonce,
            'bfx-apikey': self.api_key,
            'bfx-signature': signature
        }
    
    def _make_request(self, method: str, endpoint: str, params: Dict = None, authenticated: bool = False) -> Optional[Dict]:
        """執行 API 請求"""
        url = f"{self.base_url}{endpoint}"
        headers = {}
        
        try:
            if authenticated:
                body = ''
                if method == 'POST' and params:
                    body = str(params)
                headers.update(self._generate_auth_headers(endpoint.replace('/v2', ''), body))
            
            if method == 'GET':
                response = self.session.get(url, params=params, headers=headers, timeout=30)
            elif method == 'POST':
                response = self.session.post(url, json=params, headers=headers, timeout=30)
            else:
                raise ValueError(f"不支持的請求方法: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API 請求失敗 {method} {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"API 請求錯誤: {e}")
            return None
    
    def get_wallet_balances(self) -> Dict[str, Decimal]:
        """獲取錢包餘額"""
        try:
            response = self._make_request('POST', '/v2/auth/r/wallets', authenticated=True)
            if not response:
                return {}
            
            balances = {}
            for wallet in response:
                if len(wallet) >= 3:
                    wallet_type, currency, balance = wallet[0], wallet[1], wallet[2]
                    if wallet_type == 'funding':  # 只關心 funding 錢包
                        balances[currency] = Decimal(str(balance))
            
            logger.info(f"獲取錢包餘額成功: {dict(balances)}")
            return balances
            
        except Exception as e:
            logger.error(f"獲取錢包餘額失敗: {e}")
            return {}
    
    def get_active_funding_offers(self, currency: str) -> List[Dict]:
        """獲取活躍的放貸訂單"""
        try:
            response = self._make_request('POST', f'/v2/auth/r/funding/offers/{currency}', authenticated=True)
            if not response:
                return []
            
            logger.info(f"獲取活躍訂單成功: {len(response)} 筆")
            return response
            
        except Exception as e:
            logger.error(f"獲取活躍訂單失敗: {e}")
            return []
    
    def cancel_all_funding_offers(self, currency: str) -> bool:
        """取消所有活躍的放貸訂單"""
        try:
            active_offers = self.get_active_funding_offers(currency)
            if not active_offers:
                logger.info("沒有需要取消的訂單")
                return True
            
            cancelled_count = 0
            for offer in active_offers:
                if len(offer) >= 1:
                    offer_id = offer[0]
                    cancel_response = self._make_request(
                        'POST', 
                        '/v2/auth/w/funding/offer/cancel', 
                        {'id': offer_id},
                        authenticated=True
                    )
                    if cancel_response:
                        cancelled_count += 1
                        time.sleep(0.1)  # 避免請求過快
            
            logger.info(f"成功取消 {cancelled_count}/{len(active_offers)} 個訂單")
            return cancelled_count > 0
            
        except Exception as e:
            logger.error(f"取消訂單失敗: {e}")
            return False
    
    def submit_funding_offer(self, currency: str, amount: Decimal, rate: Decimal, period: int) -> Optional[Dict]:
        """提交放貸訂單"""
        try:
            # Bitfinex 要求利率為年化百分比 (0.01 = 1%)
            annual_rate = float(rate * 365 * 100)
            
            payload = {
                'type': 'LIMIT',
                'symbol': f'f{currency}',
                'amount': str(amount),
                'rate': str(annual_rate),
                'period': period,
                'flags': 0
            }
            
            response = self._make_request(
                'POST', 
                '/v2/auth/w/funding/offer/submit', 
                payload,
                authenticated=True
            )
            
            if response and len(response) >= 7:
                logger.info(f"提交訂單成功: {amount} {currency} @ {annual_rate:.4f}% (年化) for {period} days")
                return response
            else:
                logger.warning(f"訂單提交響應異常: {response}")
                return None
                
        except Exception as e:
            logger.error(f"提交訂單失敗: {e}")
            return None
    
    def get_funding_book(self, currency: str) -> Dict:
        """獲取資金簿數據 (用於市場分析)"""
        try:
            response = self._make_request('GET', f'/v2/book/f{currency}/P0', params={'len': '25'})
            if response:
                return {
                    'bids': response,
                    'timestamp': time.time()
                }
            return {}
            
        except Exception as e:
            logger.error(f"獲取資金簿失敗: {e}")
            return {}

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
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT 1')
        except Exception as e:
            logger.error(f"數據庫連接失敗: {e}")
            raise
    
    def get_connection(self):
        """獲取數據庫連接"""
        return psycopg2.connect(self.db_url)
    
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
        self.api = SimpleBitfinexAPI()
        
        # 數據庫管理
        self.db = SimpleDatabase()
        self.db.initialize_tables()
        
        # 配置參數
        self.currency = config('LENDING_CURRENCY', default='USD')
        self.min_amount = Decimal(config('MIN_ORDER_AMOUNT', default='50'))
        self.max_amount = Decimal(config('MAX_LOAN_AMOUNT', default='10000'))
        self.run_interval = int(config('RUN_INTERVAL_MINUTES', default='30'))
        
        # Telegram 配置 (可選)
        self.telegram_token = config('TELEGRAM_BOT_TOKEN', default='')
        self.telegram_chat_id = config('TELEGRAM_CHAT_ID', default='')
        
        logger.info(f"✅ 配置加載完成:")
        logger.info(f"   💰 放貸幣種: {self.currency}")
        logger.info(f"   💵 訂單範圍: {self.min_amount} - {self.max_amount}")
        logger.info(f"   ⏰ 運行間隔: {self.run_interval} 分鐘")
        logger.info(f"   📱 Telegram: {'已配置' if self.telegram_token else '未配置'}")
    
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
    
    def ladder_strategy(self, available_balance: Decimal) -> List[Dict]:
        """階梯策略 - 在多個利率水平分散資金"""
        if available_balance < self.min_amount:
            logger.warning(f"可用餘額 {available_balance} 低於最小訂單金額 {self.min_amount}")
            return []
        
        # 5階梯配置
        ladder_count = 5
        base_rate = Decimal('0.0001')  # 0.01% 日利率 (3.65% 年化)
        rate_increment = Decimal('0.0001')  # 每階梯增加 0.01%
        period_days = 2  # 2天期
        
        # 計算每階梯金額
        amount_per_ladder = min(available_balance / ladder_count, self.max_amount / ladder_count)
        
        orders = []
        total_amount = Decimal('0')
        
        for i in range(ladder_count):
            if amount_per_ladder >= self.min_amount:
                rate = base_rate + (rate_increment * i)
                amount = round(amount_per_ladder, 2)
                
                orders.append({
                    'amount': amount,
                    'rate': rate,
                    'period': period_days,
                    'annual_rate_pct': float(rate * 365 * 100)  # 轉換為年化百分比
                })
                total_amount += amount
        
        logger.info(f"🎯 階梯策略生成:")
        logger.info(f"   📊 階梯數量: {len(orders)}")
        logger.info(f"   💰 總金額: {total_amount} {self.currency}")
        logger.info(f"   📈 利率範圍: {base_rate*365*100:.2f}% - {(base_rate + rate_increment * (ladder_count-1))*365*100:.2f}% (年化)")
        
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
            
            # 2. 獲取可用餘額
            logger.info("2️⃣ 獲取可用餘額...")
            balances = self.api.get_wallet_balances()
            available = balances.get(self.currency, Decimal('0'))
            
            if available <= 0:
                logger.warning("⚠️  沒有可用餘額，跳過本次運行")
                self._update_status(Decimal('0'), Decimal('0'), 0, 'no_balance')
                return
            
            logger.info(f"💰 可用餘額: {available} {self.currency}")
            
            # 3. 執行階梯策略
            logger.info("3️⃣ 執行階梯策略...")
            orders = self.ladder_strategy(available)
            
            if not orders:
                logger.warning("⚠️  策略未生成訂單")
                self._update_status(available, Decimal('0'), 0, 'no_orders')
                return
            
            # 4. 提交訂單
            logger.info("4️⃣ 提交放貸訂單...")
            successful_orders = 0
            total_lending = Decimal('0')
            
            for i, order in enumerate(orders, 1):
                logger.info(f"   提交訂單 {i}/{len(orders)}: {order['amount']} {self.currency} @ {order['annual_rate_pct']:.4f}% (年化)")
                
                result = self.api.submit_funding_offer(
                    self.currency,
                    order['amount'],
                    order['rate'],
                    order['period']
                )
                
                if result:
                    successful_orders += 1
                    total_lending += order['amount']
                    time.sleep(1)  # 避免請求過快
            
            # 5. 更新系統狀態
            logger.info("5️⃣ 更新系統狀態...")
            self._update_status(available, total_lending, successful_orders, 'success')
            
            # 6. 發送成功通知
            cycle_end = datetime.now()
            runtime = (cycle_end - cycle_start).total_seconds()
            
            success_message = f"""
🤖 <b>SimpleLendingBot 運行報告</b>

⏰ <b>運行時間</b>: {cycle_start.strftime('%Y-%m-%d %H:%M:%S')}
💰 <b>可用餘額</b>: {available:,.2f} {self.currency}
📊 <b>成功訂單</b>: {successful_orders}/{len(orders)}
💵 <b>放貸金額</b>: {total_lending:,.2f} {self.currency}
📈 <b>資金利用率</b>: {(total_lending/available*100):.1f}%

🎯 <b>策略</b>: 5階梯放貸
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
📊 <b>策略</b>: 5階梯放貸
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