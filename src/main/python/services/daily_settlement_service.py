import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
import asyncio
from dataclasses import dataclass

from src.main.python.models.daily_earnings import (
    DailyEarnings, DailyEarningsCreate, SettlementStatus
)
from src.main.python.models.active_position import ActivePosition
from src.main.python.repositories.daily_earnings_repository import DailyEarningsRepository
from src.main.python.repositories.interest_payment_repository import InterestPaymentRepository
from src.main.python.api.bitfinex_api_client import BitfinexApiClient
from src.main.python.core.exceptions import SettlementError, BitfinexAPIError

log = logging.getLogger(__name__)


@dataclass
class SettlementInput:
    """結算輸入數據"""
    date: date
    currency: str
    positions: List[ActivePosition]
    
    # 從API獲取的數據
    exchange_daily_interest: Decimal
    exchange_wallet_balances: Dict[str, Decimal]
    market_rates: Dict[str, Decimal]


@dataclass
class SettlementResult:
    """結算結果"""
    success: bool
    daily_earnings: Optional[DailyEarnings]
    error_message: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class DailySettlementService:
    """每日結算服務 - 微服務架構的核心"""
    
    def __init__(self, 
                 daily_earnings_repo: DailyEarningsRepository,
                 interest_payment_repo: InterestPaymentRepository,
                 api_client: BitfinexApiClient):
        self.daily_earnings_repo = daily_earnings_repo
        self.interest_payment_repo = interest_payment_repo
        self.api_client = api_client
        
        # 結算配置
        self.settlement_timeout = 300  # 5分鐘超時
        self.max_retries = 3
        
    async def perform_daily_settlement(self, settlement_date: date, 
                                     currency: str) -> SettlementResult:
        """執行每日結算 - 主要業務邏輯"""
        
        log.info(f"開始執行每日結算: {settlement_date} {currency}")
        
        try:
            # 1. 標記結算開始
            await self._mark_settlement_status(settlement_date, currency, SettlementStatus.IN_PROGRESS)
            
            # 2. 收集結算所需數據
            settlement_input = await self._collect_settlement_data(settlement_date, currency)
            
            # 3. 執行核心結算邏輯
            daily_earnings = await self._calculate_daily_earnings(settlement_input)
            
            # 4. 保存結算結果
            saved_earnings = self.daily_earnings_repo.save(daily_earnings)
            
            # 5. 標記結算完成
            await self._mark_settlement_status(settlement_date, currency, SettlementStatus.COMPLETED)
            
            log.info(f"結算完成: {settlement_date} {currency}, 收益: {daily_earnings.total_interest}")
            
            return SettlementResult(
                success=True,
                daily_earnings=saved_earnings
            )
            
        except Exception as e:
            log.error(f"結算失敗: {settlement_date} {currency}, 錯誤: {e}")
            
            # 標記結算失敗
            await self._mark_settlement_status(settlement_date, currency, SettlementStatus.FAILED)
            
            return SettlementResult(
                success=False,
                daily_earnings=None,
                error_message=str(e)
            )
    
    async def _collect_settlement_data(self, settlement_date: date, 
                                     currency: str) -> SettlementInput:
        """收集結算所需的所有數據"""
        
        log.debug(f"收集結算數據: {settlement_date} {currency}")
        
        try:
            # 並行收集多個數據源
            tasks = [
                self._get_daily_interest_from_exchange(settlement_date, currency),
                self._get_wallet_balances(currency),
                self._get_market_rates(currency),
                self._get_active_positions(settlement_date, currency)
            ]
            
            results = await asyncio.gather(*tasks)
            
            return SettlementInput(
                date=settlement_date,
                currency=currency,
                positions=results[3],
                exchange_daily_interest=results[0],
                exchange_wallet_balances=results[1],
                market_rates=results[2]
            )
            
        except Exception as e:
            log.error(f"數據收集失敗: {e}")
            raise SettlementError(f"Failed to collect settlement data: {e}")
    
    async def _calculate_daily_earnings(self, input_data: SettlementInput) -> DailyEarningsCreate:
        """計算每日收益 - 核心業務邏輯"""
        
        log.debug(f"計算每日收益: {input_data.date} {input_data.currency}")
        
        # 1. 基本收益計算
        total_interest = input_data.exchange_daily_interest
        
        # 2. 資金部署分析
        deployed_amount = sum(pos.amount for pos in input_data.positions if pos.status == 'ACTIVE')
        available_amount = input_data.exchange_wallet_balances.get('available', Decimal('0'))
        total_amount = deployed_amount + available_amount
        
        # 3. 利率和收益率計算
        if deployed_amount > 0:
            daily_return_rate = total_interest / deployed_amount
            weighted_avg_rate = self._calculate_weighted_avg_rate(input_data.positions)
        else:
            daily_return_rate = Decimal('0')
            weighted_avg_rate = Decimal('0')
        
        # 4. 資金利用率
        utilization_rate = (deployed_amount / total_amount * 100) if total_amount > 0 else Decimal('0')
        
        # 5. 年化收益率
        annualized_return = daily_return_rate * 365 * 100
        
        # 6. 策略分析
        strategy_stats = self._analyze_strategy_performance(input_data.positions)
        
        # 7. 市場競爭力分析
        market_competitiveness = self._calculate_market_competitiveness(
            weighted_avg_rate, 
            input_data.market_rates.get('avg_rate', Decimal('0'))
        )
        
        return DailyEarningsCreate(
            date=input_data.date,
            currency=input_data.currency,
            total_interest=total_interest,
            deployed_amount=deployed_amount,
            available_amount=available_amount,
            weighted_avg_rate=weighted_avg_rate,
            utilization_rate=utilization_rate,
            daily_return_rate=daily_return_rate,
            annualized_return=annualized_return,
            primary_strategy=strategy_stats['primary_strategy'],
            total_orders_placed=strategy_stats['total_orders'],
            orders_success_rate=strategy_stats['success_rate'],
            market_avg_rate=input_data.market_rates.get('avg_rate'),
            market_competitiveness=market_competitiveness
        )
    
    def _calculate_weighted_avg_rate(self, positions: List[ActivePosition]) -> Decimal:
        """計算加權平均利率"""
        if not positions:
            return Decimal('0')
        
        total_weighted = sum(pos.amount * pos.rate for pos in positions)
        total_amount = sum(pos.amount for pos in positions)
        
        return total_weighted / total_amount if total_amount > 0 else Decimal('0')
    
    def _analyze_strategy_performance(self, positions: List[ActivePosition]) -> Dict[str, Any]:
        """分析策略表現"""
        if not positions:
            return {
                'primary_strategy': 'NONE',
                'total_orders': 0,
                'success_rate': Decimal('0')
            }
        
        # 統計策略使用情況
        strategy_counts = {}
        for pos in positions:
            strategy_counts[pos.strategy_name] = strategy_counts.get(pos.strategy_name, 0) + 1
        
        # 找出主要策略
        primary_strategy = max(strategy_counts, key=strategy_counts.get)
        
        # 計算成功率 (活躍或已關閉的頭寸視為成功)
        successful_positions = sum(1 for pos in positions 
                                 if pos.status in ['ACTIVE', 'CLOSED'])
        success_rate = (Decimal(str(successful_positions)) / Decimal(str(len(positions))) * 100 
                       if positions else Decimal('0'))
        
        return {
            'primary_strategy': primary_strategy,
            'total_orders': len(positions),
            'success_rate': success_rate
        }
    
    def _calculate_market_competitiveness(self, our_rate: Decimal, 
                                        market_rate: Decimal) -> Optional[Decimal]:
        """計算市場競爭力指標"""
        if market_rate and market_rate > 0:
            return (our_rate / market_rate * 100)
        return None
    
    async def _get_daily_interest_from_exchange(self, date: date, currency: str) -> Decimal:
        """從交易所獲取當日利息總額"""
        try:
            # 獲取指定日期的利息支付記錄
            start_timestamp = int(datetime.combine(date, datetime.min.time()).timestamp() * 1000)
            end_timestamp = int(datetime.combine(date, datetime.max.time()).timestamp() * 1000)
            
            ledgers = self.api_client.get_ledgers(
                currency=currency,
                start=start_timestamp,
                end=end_timestamp,
                category=28  # 利息支付類別
            )
            
            # 計算總利息
            total_interest = sum(Decimal(str(entry[3])) for entry in ledgers if entry[3] > 0)
            
            log.debug(f"從交易所獲取利息: {date} {currency} = {total_interest}")
            return total_interest
            
        except BitfinexAPIError as e:
            log.warning(f"無法從交易所獲取利息數據: {e}, 使用本地數據")
            # 回退到本地數據
            return await self._get_local_daily_interest(date, currency)
    
    async def _get_local_daily_interest(self, date: date, currency: str) -> Decimal:
        """從本地數據庫獲取當日利息"""
        payments = self.interest_payment_repo.get_payments_by_date(date, currency)
        return sum(payment.amount for payment in payments)
    
    async def _get_wallet_balances(self, currency: str) -> Dict[str, Decimal]:
        """獲取錢包餘額"""
        try:
            balances = self.api_client.get_wallet_balances()
            
            result = {}
            for wallet in balances:
                wallet_type, wallet_currency, balance, _, available = wallet
                if wallet_currency == currency and wallet_type == 'funding':
                    result['balance'] = Decimal(str(balance))
                    result['available'] = Decimal(str(available))
                    break
            
            return result
            
        except Exception as e:
            log.error(f"獲取錢包餘額失敗: {e}")
            return {'balance': Decimal('0'), 'available': Decimal('0')}
    
    async def _get_market_rates(self, currency: str) -> Dict[str, Decimal]:
        """獲取市場利率數據"""
        try:
            funding_book = self.api_client.get_funding_book(f'f{currency}', limit=10)
            
            if funding_book and 'bids' in funding_book and funding_book['bids']:
                # 計算前5檔的平均利率
                top_rates = [Decimal(str(bid[0])) for bid in funding_book['bids'][:5]]
                avg_rate = sum(top_rates) / len(top_rates)
                
                return {
                    'top_rate': top_rates[0],
                    'avg_rate': avg_rate
                }
            
            return {}
            
        except Exception as e:
            log.error(f"獲取市場利率失敗: {e}")
            return {}
    
    async def _get_active_positions(self, date: date, currency: str) -> List[ActivePosition]:
        """獲取活躍頭寸 (這裡需要與Position Management Service整合)"""
        # TODO: 整合Position Management Service
        # 目前返回空列表，後續會在Position Management Service中實現
        return []
    
    async def _mark_settlement_status(self, date: date, currency: str, 
                                    status: SettlementStatus):
        """標記結算狀態"""
        try:
            # 如果記錄不存在，先創建一個基本記錄
            existing = self.daily_earnings_repo.get_by_date(date, currency)
            if not existing and status == SettlementStatus.IN_PROGRESS:
                placeholder = DailyEarningsCreate(
                    date=date,
                    currency=currency,
                    total_interest=Decimal('0'),
                    deployed_amount=Decimal('0'),
                    available_amount=Decimal('0'),
                    weighted_avg_rate=Decimal('0'),
                    utilization_rate=Decimal('0'),
                    daily_return_rate=Decimal('0'),
                    annualized_return=Decimal('0'),
                    primary_strategy='PENDING',
                    total_orders_placed=0,
                    orders_success_rate=Decimal('0')
                )
                self.daily_earnings_repo.save(placeholder)
            
            # 更新狀態
            self.daily_earnings_repo.update_settlement_status(date, currency, status)
            
        except Exception as e:
            log.error(f"更新結算狀態失敗: {e}")
    
    async def get_settlement_status(self, date: date, currency: str) -> Optional[SettlementStatus]:
        """獲取結算狀態"""
        try:
            earnings = self.daily_earnings_repo.get_by_date(date, currency)
            return earnings.settlement_status if earnings else None
            
        except Exception as e:
            log.error(f"獲取結算狀態失敗: {e}")
            return None
    
    async def retry_failed_settlement(self, date: date, currency: str) -> SettlementResult:
        """重試失敗的結算"""
        log.info(f"重試結算: {date} {currency}")
        
        current_status = await self.get_settlement_status(date, currency)
        if current_status != SettlementStatus.FAILED:
            return SettlementResult(
                success=False,
                daily_earnings=None,
                error_message=f"Settlement status is {current_status}, cannot retry"
            )
        
        return await self.perform_daily_settlement(date, currency)