import pytest
import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

from src.main.python.services.daily_settlement_service import (
    DailySettlementService, SettlementInput, SettlementResult
)
from src.main.python.models.daily_earnings import DailyEarningsCreate, SettlementStatus
from src.main.python.models.active_position import ActivePosition, PositionStatus
from src.main.python.core.exceptions import SettlementError


class TestDailySettlementService:
    """Daily Settlement Service 測試套件"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """創建模擬依賴"""
        daily_earnings_repo = Mock()
        interest_payment_repo = Mock()
        api_client = Mock()
        
        return {
            'daily_earnings_repo': daily_earnings_repo,
            'interest_payment_repo': interest_payment_repo,
            'api_client': api_client
        }
    
    @pytest.fixture
    def settlement_service(self, mock_dependencies):
        """創建測試用的結算服務"""
        return DailySettlementService(
            daily_earnings_repo=mock_dependencies['daily_earnings_repo'],
            interest_payment_repo=mock_dependencies['interest_payment_repo'],
            api_client=mock_dependencies['api_client']
        )
    
    @pytest.fixture
    def sample_positions(self):
        """創建樣本頭寸數據"""
        return [
            ActivePosition(
                position_id="pos_001",
                currency="USD",
                amount=Decimal('1000.0'),
                rate=Decimal('0.0001'),
                period=2,
                opened_at=datetime.now() - timedelta(hours=12),
                expected_return=Decimal('0.2'),
                strategy_name="laddering",
                status=PositionStatus.ACTIVE
            ),
            ActivePosition(
                position_id="pos_002",
                currency="USD",
                amount=Decimal('2000.0'),
                rate=Decimal('0.00015'),
                period=2,
                opened_at=datetime.now() - timedelta(hours=8),
                expected_return=Decimal('0.6'),
                strategy_name="adaptive_laddering",
                status=PositionStatus.ACTIVE
            )
        ]
    
    @pytest.fixture
    def sample_settlement_input(self, sample_positions):
        """創建樣本結算輸入"""
        return SettlementInput(
            date=date.today(),
            currency="USD",
            positions=sample_positions,
            exchange_daily_interest=Decimal('0.8'),
            exchange_wallet_balances={
                'balance': Decimal('5000.0'),
                'available': Decimal('2000.0')
            },
            market_rates={
                'top_rate': Decimal('0.00012'),
                'avg_rate': Decimal('0.00011')
            }
        )

    @pytest.mark.asyncio
    async def test_successful_daily_settlement(self, settlement_service, mock_dependencies, 
                                             sample_settlement_input):
        """測試成功的日結算流程"""
        
        # 模擬依賴的返回值
        mock_dependencies['daily_earnings_repo'].get_by_date.return_value = None
        mock_dependencies['daily_earnings_repo'].save.return_value = Mock(id=1)
        mock_dependencies['daily_earnings_repo'].update_settlement_status.return_value = True
        
        # 模擬數據收集
        with patch.object(settlement_service, '_collect_settlement_data', 
                         return_value=sample_settlement_input):
            
            result = await settlement_service.perform_daily_settlement(
                date.today(), "USD"
            )
        
        # 驗證結果
        assert result.success is True
        assert result.daily_earnings is not None
        assert result.error_message is None
        
        # 驗證調用了正確的方法
        mock_dependencies['daily_earnings_repo'].save.assert_called_once()
        assert mock_dependencies['daily_earnings_repo'].update_settlement_status.call_count == 2
    
    @pytest.mark.asyncio
    async def test_settlement_failure_handling(self, settlement_service, mock_dependencies):
        """測試結算失敗的處理"""
        
        # 模擬數據收集失敗
        with patch.object(settlement_service, '_collect_settlement_data', 
                         side_effect=Exception("API Error")):
            
            result = await settlement_service.perform_daily_settlement(
                date.today(), "USD"
            )
        
        # 驗證錯誤處理
        assert result.success is False
        assert "API Error" in result.error_message
        
        # 驗證標記為失敗狀態
        mock_dependencies['daily_earnings_repo'].update_settlement_status.assert_called_with(
            date.today(), "USD", SettlementStatus.FAILED
        )
    
    def test_calculate_weighted_avg_rate(self, settlement_service, sample_positions):
        """測試加權平均利率計算"""
        
        # 計算預期結果
        # pos_001: 1000 * 0.0001 = 0.1
        # pos_002: 2000 * 0.00015 = 0.3
        # 總計: 0.4 / 3000 = 0.0001333...
        expected_rate = Decimal('0.4') / Decimal('3000')
        
        result = settlement_service._calculate_weighted_avg_rate(sample_positions)
        
        # 驗證結果 (允許小數點誤差)
        assert abs(result - expected_rate) < Decimal('0.0000001')
    
    def test_calculate_weighted_avg_rate_empty_positions(self, settlement_service):
        """測試空頭寸列表的加權平均利率計算"""
        result = settlement_service._calculate_weighted_avg_rate([])
        assert result == Decimal('0')
    
    def test_analyze_strategy_performance(self, settlement_service, sample_positions):
        """測試策略表現分析"""
        
        result = settlement_service._analyze_strategy_performance(sample_positions)
        
        # 驗證結果結構
        assert 'primary_strategy' in result
        assert 'total_orders' in result
        assert 'success_rate' in result
        
        # 驗證具體值
        assert result['total_orders'] == 2
        assert result['success_rate'] == Decimal('100')  # 所有頭寸都是ACTIVE
        assert result['primary_strategy'] in ['laddering', 'adaptive_laddering']
    
    def test_analyze_strategy_performance_empty_positions(self, settlement_service):
        """測試空頭寸的策略分析"""
        
        result = settlement_service._analyze_strategy_performance([])
        
        assert result['primary_strategy'] == 'NONE'
        assert result['total_orders'] == 0
        assert result['success_rate'] == Decimal('0')
    
    def test_calculate_market_competitiveness(self, settlement_service):
        """測試市場競爭力計算"""
        
        our_rate = Decimal('0.00012')
        market_rate = Decimal('0.00010')
        
        result = settlement_service._calculate_market_competitiveness(our_rate, market_rate)
        
        # 120% 競爭力 (我們的利率比市場高20%)
        expected = Decimal('120')
        assert result == expected
    
    def test_calculate_market_competitiveness_zero_market_rate(self, settlement_service):
        """測試零市場利率的競爭力計算"""
        
        result = settlement_service._calculate_market_competitiveness(
            Decimal('0.00012'), Decimal('0')
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_collect_settlement_data_integration(self, settlement_service, mock_dependencies):
        """測試數據收集整合"""
        
        # 模擬API返回
        mock_dependencies['api_client'].get_ledgers.return_value = [
            [123, 'funding', 'USD', 0.5, 1000.5, 1234567890, 'Interest payment', 28]
        ]
        mock_dependencies['api_client'].get_wallet_balances.return_value = [
            ['funding', 'USD', 5000.0, 0.0, 2000.0]
        ]
        mock_dependencies['api_client'].get_funding_book.return_value = {
            'bids': [[0.00012, 1000], [0.00011, 2000]]
        }
        
        # 模擬頭寸查詢 (目前返回空列表)
        with patch.object(settlement_service, '_get_active_positions', return_value=[]):
            
            result = await settlement_service._collect_settlement_data(date.today(), "USD")
        
        # 驗證結果
        assert result.date == date.today()
        assert result.currency == "USD"
        assert result.exchange_daily_interest == Decimal('0.5')
        assert result.exchange_wallet_balances['available'] == Decimal('2000.0')
        assert result.market_rates['top_rate'] == Decimal('0.00012')
    
    @pytest.mark.asyncio
    async def test_calculate_daily_earnings_complete_flow(self, settlement_service, 
                                                        sample_settlement_input):
        """測試完整的每日收益計算流程"""
        
        result = await settlement_service._calculate_daily_earnings(sample_settlement_input)
        
        # 驗證基本字段
        assert result.date == sample_settlement_input.date
        assert result.currency == sample_settlement_input.currency
        assert result.total_interest == Decimal('0.8')
        
        # 驗證計算結果
        assert result.deployed_amount == Decimal('3000.0')  # 1000 + 2000
        assert result.available_amount == Decimal('2000.0')
        
        # 驗證利率計算
        expected_weighted_rate = (Decimal('1000') * Decimal('0.0001') + 
                                Decimal('2000') * Decimal('0.00015')) / Decimal('3000')
        assert abs(result.weighted_avg_rate - expected_weighted_rate) < Decimal('0.0000001')
        
        # 驗證收益率
        expected_daily_return = Decimal('0.8') / Decimal('3000.0')
        assert abs(result.daily_return_rate - expected_daily_return) < Decimal('0.0000001')
        
        # 驗證資金利用率
        expected_utilization = Decimal('3000') / Decimal('5000') * 100  # 60%
        assert result.utilization_rate == expected_utilization
        
        # 驗證年化收益率
        expected_annualized = expected_daily_return * 365 * 100
        assert abs(result.annualized_return - expected_annualized) < Decimal('0.001')
    
    @pytest.mark.asyncio  
    async def test_retry_failed_settlement(self, settlement_service, mock_dependencies):
        """測試重試失敗的結算"""
        
        # 模擬失敗狀態
        mock_dependencies['daily_earnings_repo'].get_by_date.return_value = Mock(
            settlement_status=SettlementStatus.FAILED
        )
        
        # 模擬重試成功
        with patch.object(settlement_service, 'perform_daily_settlement', 
                         return_value=SettlementResult(success=True, daily_earnings=Mock())):
            
            result = await settlement_service.retry_failed_settlement(date.today(), "USD")
        
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_retry_non_failed_settlement(self, settlement_service, mock_dependencies):
        """測試重試非失敗狀態的結算"""
        
        # 模擬完成狀態
        mock_dependencies['daily_earnings_repo'].get_by_date.return_value = Mock(
            settlement_status=SettlementStatus.COMPLETED
        )
        
        result = await settlement_service.retry_failed_settlement(date.today(), "USD")
        
        assert result.success is False
        assert "cannot retry" in result.error_message
    
    @pytest.mark.asyncio
    async def test_get_settlement_status(self, settlement_service, mock_dependencies):
        """測試獲取結算狀態"""
        
        # 模擬返回
        mock_earnings = Mock()
        mock_earnings.settlement_status = SettlementStatus.COMPLETED
        mock_dependencies['daily_earnings_repo'].get_by_date.return_value = mock_earnings
        
        result = await settlement_service.get_settlement_status(date.today(), "USD")
        
        assert result == SettlementStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_get_settlement_status_not_found(self, settlement_service, mock_dependencies):
        """測試獲取不存在記錄的結算狀態"""
        
        mock_dependencies['daily_earnings_repo'].get_by_date.return_value = None
        
        result = await settlement_service.get_settlement_status(date.today(), "USD")
        
        assert result is None


@pytest.mark.integration
class TestDailySettlementServiceIntegration:
    """Daily Settlement Service 整合測試"""
    
    @pytest.fixture
    def real_database_config(self):
        """真實數據庫配置 (用於整合測試)"""
        # 這裡應該設置測試數據庫
        pass
    
    @pytest.mark.asyncio
    async def test_end_to_end_settlement_flow(self):
        """端到端結算流程測試"""
        # 此測試需要真實的數據庫和API連接
        # 在CI/CD環境中可以使用測試數據庫
        pytest.skip("Requires real database and API connections")
    
    @pytest.mark.asyncio
    async def test_concurrent_settlement_handling(self):
        """測試並發結算處理"""
        # 測試多個結算請求的並發處理
        pytest.skip("Requires complex test setup")


if __name__ == "__main__":
    # 運行測試
    pytest.main([__file__, "-v", "--tb=short"])