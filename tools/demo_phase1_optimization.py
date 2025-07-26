#!/usr/bin/env python3
"""
第一階段優化演示腳本

展示新增的 LendingOrder 和 InterestPayment 模型功能，
以及它們如何整合到主程式中進行收益分析。
"""

import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

# 添加項目根目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.main.python.models.lending_order import LendingOrder, OrderStatus
from src.main.python.models.interest_payment import InterestPayment, PaymentType

def demonstrate_lending_order_features():
    """演示 LendingOrder 模型的新功能"""
    print("🏦 === LendingOrder 模型功能演示 ===")
    
    # 創建一個放貸訂單
    order = LendingOrder(
        order_id=12345,
        symbol="fUSD",
        amount=Decimal('1000'),
        rate=Decimal('0.0001'),  # 0.01% 日利率
        period=7,
        strategy_name="ConservativeStrategy",
        strategy_params={"min_rate": 0.0001, "max_amount": 1000}
    )
    
    print(f"📝 創建訂單: ID={order.order_id}, 金額=${order.amount}, 利率={order.rate*100:.4f}%")
    print(f"🎯 策略: {order.strategy_name}")
    print(f"⏱️  期限: {order.period} 天")
    
    # 計算預期收益
    expected_interest = order.calculate_expected_interest()
    print(f"💰 預期利息: ${expected_interest}")
    
    # 模擬 API 響應更新
    print("\n📡 模擬 Bitfinex API 響應更新...")
    api_response = {
        'amount_executed': '800',  # 部分成交
        'rate': '0.00012',        # 實際利率稍高
        'status': 'ACTIVE',
        'mts_created': int(datetime.now().timestamp() * 1000)
    }
    
    order.update_from_api_response(api_response)
    print(f"✅ 訂單已更新: 執行金額=${order.executed_amount}, 實際利率={order.executed_rate*100:.4f}%")
    print(f"📊 狀態: {order.status.value}")
    
    # 重新計算預期收益
    updated_expected = order.calculate_expected_interest()
    print(f"🔄 更新後預期利息: ${updated_expected}")
    
    # 演示各種分析方法
    print(f"🔍 分析結果:")
    print(f"  - 是否活躍: {order.is_active()}")
    print(f"  - 還款模式: {order.get_repayment_pattern()}")
    print(f"  - 驗證完整性: {order.validate_completion()}")
    
    return order

def demonstrate_interest_payment_features():
    """演示 InterestPayment 模型的新功能"""
    print("\n💳 === InterestPayment 模型功能演示 ===")
    
    # 創建利息支付記錄
    payments = []
    
    # 每日利息支付
    for day in range(5):
        payment = InterestPayment(
            currency="USD",
            amount=Decimal('0.08') + Decimal(str(day * 0.01)),  # 變動的利息
            paid_at=datetime.now() - timedelta(days=4-day),
            order_id=12345,
            payment_type=PaymentType.DAILY_INTEREST,
            principal_amount=Decimal('800'),  # 對應執行金額
            fee_amount=Decimal('0.008'),
            daily_rate=Decimal('0.0001')
        )
        payments.append(payment)
    
    # 最終結算
    settlement = InterestPayment(
        currency="USD",
        amount=Decimal('0.15'),
        paid_at=datetime.now(),
        order_id=12345,
        payment_type=PaymentType.SETTLEMENT,
        principal_amount=Decimal('800'),
        fee_amount=Decimal('0.015')
    )
    payments.append(settlement)
    
    print(f"📋 創建了 {len(payments)} 筆利息支付記錄")
    
    # 分析支付記錄
    total_gross = sum(p.amount for p in payments)
    total_net = sum(p.calculate_net_amount() for p in payments)
    total_fees = sum(p.fee_amount or Decimal('0') for p in payments)
    
    print(f"💰 總收益分析:")
    print(f"  - 毛收益: ${total_gross:.4f}")
    print(f"  - 淨收益: ${total_net:.4f}")
    print(f"  - 總手續費: ${total_fees:.4f}")
    
    # 按類型分組
    grouped = InterestPayment.group_by_payment_type(payments)
    for payment_type, group in grouped.items():
        count = len(group)
        amount = sum(p.calculate_net_amount() for p in group)
        print(f"  - {payment_type.value}: {count} 筆, ${amount:.4f}")
    
    # 演示異常檢測
    print(f"\n🔍 異常檢測演示:")
    for i, payment in enumerate(payments[:2]):
        anomalies = payment.detect_anomalies()
        if anomalies:
            print(f"  - 支付 {i+1}: {', '.join(anomalies)}")
        else:
            print(f"  - 支付 {i+1}: 正常")
    
    return payments

def demonstrate_integrated_analysis(order, payments):
    """演示整合分析功能"""
    print("\n🔬 === 整合分析演示 ===")
    
    # 模擬關聯（實際會通過 Repository 層實現）
    def mock_get_related_payments():
        return [p for p in payments if p.order_id == order.order_id]
    
    # 臨時替換方法進行演示
    order.get_related_interest_payments = mock_get_related_payments
    
    # 計算實際收益
    actual_interest = order.calculate_actual_total_interest()
    expected_interest = order.calculate_expected_interest()
    variance = order.calculate_interest_variance()
    variance_pct = order.calculate_interest_variance_percentage()
    
    print(f"📊 收益對比分析:")
    print(f"  - 預期利息: ${expected_interest:.4f}")
    print(f"  - 實際利息: ${actual_interest:.4f}")
    print(f"  - 絕對差異: ${variance:.4f}")
    if variance_pct:
        print(f"  - 差異百分比: {variance_pct:.2f}%")
    
    # 計算實際收益率
    actual_rate = order.calculate_actual_daily_rate()
    if actual_rate:
        efficiency = order.calculate_yield_efficiency()
        print(f"📈 收益率分析:")
        print(f"  - 預期日利率: {order.rate*100:.4f}%")
        print(f"  - 實際日利率: {actual_rate*100:.4f}%")
        if efficiency:
            print(f"  - 收益效率: {efficiency*100:.2f}%")
    
    # 時間線分析
    timeline = order.get_interest_payment_timeline()
    if timeline:
        print(f"📅 支付時間線:")
        for date, amount in sorted(timeline.items()):
            print(f"  - {date}: ${amount:.4f}")
    
    # 還款分析
    is_early = order.is_early_repaid()
    actual_days = order.get_actual_period_days()
    pattern = order.get_repayment_pattern()
    
    print(f"⏰ 還款分析:")
    print(f"  - 預期期限: {order.period} 天")
    if actual_days:
        print(f"  - 實際期限: {actual_days} 天")
    print(f"  - 提前還款: {'是' if is_early else '否'}")
    print(f"  - 還款模式: {pattern}")

def demonstrate_ledger_parsing():
    """演示 Ledger 數據解析功能"""
    print("\n🔍 === Ledger 數據解析演示 ===")
    
    # 模擬 Bitfinex Ledger API 響應
    ledger_entries = [
        {
            'id': 67890,
            'currency': 'USD',
            'amount': 0.08,
            'mts': int((datetime.now() - timedelta(days=2)).timestamp() * 1000),
            'description': 'Funding payment for offer #12345'
        },
        {
            'id': 67891,
            'currency': 'USD',
            'amount': 0.15,
            'mts': int(datetime.now().timestamp() * 1000),
            'description': 'Settlement funding payment offer #12345'
        },
        {
            'id': 67892,
            'currency': 'USD',
            'amount': -0.01,
            'mts': int(datetime.now().timestamp() * 1000),
            'description': 'Funding fee for offer #12345'
        }
    ]
    
    print(f"📋 解析 {len(ledger_entries)} 個 Ledger 條目:")
    
    parsed_payments = []
    for entry in ledger_entries:
        try:
            payment = InterestPayment.from_ledger_entry(entry)
            parsed_payments.append(payment)
            
            print(f"✅ Ledger {entry['id']}:")
            print(f"   金額: ${payment.amount}")
            print(f"   類型: {payment.payment_type.value}")
            print(f"   關聯訂單: {payment.order_id}")
            print(f"   是否手續費: {'是' if payment.is_fee_deduction() else '否'}")
            
        except Exception as e:
            print(f"❌ Ledger {entry['id']} 解析失敗: {e}")
    
    return parsed_payments

def main():
    """主演示函數"""
    print("🚀 第一階段優化功能演示")
    print("=" * 50)
    
    try:
        # 1. 演示 LendingOrder 功能
        order = demonstrate_lending_order_features()
        
        # 2. 演示 InterestPayment 功能
        payments = demonstrate_interest_payment_features()
        
        # 3. 演示整合分析
        demonstrate_integrated_analysis(order, payments)
        
        # 4. 演示 Ledger 解析
        parsed_payments = demonstrate_ledger_parsing()
        
        print("\n🎉 === 演示完成 ===")
        print("第一階段優化成功實現:")
        print("✅ 增強的 LendingOrder 模型")
        print("✅ 增強的 InterestPayment 模型") 
        print("✅ 實際 vs 預期收益分析")
        print("✅ 自動 Ledger 數據解析")
        print("✅ 主程式整合 (下單記錄)")
        print("✅ 基本收益追蹤框架")
        
        print("\n📋 下一步 (第二階段):")
        print("🔧 實現 Repository 層")
        print("🗄️ 數據庫操作集成")
        print("⏰ 定期同步機制")
        print("📊 完整收益報告生成")
        
    except Exception as e:
        print(f"\n❌ 演示過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 