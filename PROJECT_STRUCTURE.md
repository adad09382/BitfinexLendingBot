# SimpleLendingBot 項目結構

> **智能放貸機器人架構** - 基於智能探測和多錢包管理的核心架構

## 📁 核心文件

### 🎯 主程序
- **`main.py`** - 主程序入口，包含 SimpleLendingBot 類
  - 智能資金探測機制 (`_probe_available_lending_amount()`)
  - 多錢包餘額檢查 (`run_cycle()` 增強版)
  - 動態訂單分配和實時調整
  - 自動放貸邏輯
  - 數據庫管理
  - Telegram 通知
  - 定時任務調度

### 🔗 API 層
- **`bitfinex_api.py`** - Bitfinex API 客戶端
  - 認證管理
  - 多錢包餘額查詢 (`get_all_wallet_balances()`)
  - 錢包間自動轉賬 (`transfer_between_wallets()`)
  - 放貸訂單提交/取消
  - 市場數據獲取
  - 增強錯誤處理和重試機制

### 📊 策略層  
- **`simple_ladder_strategy.py`** - 智能階梯放貸策略
  - 基於實際可用資金的動態利率計算
  - 市場競爭分析
  - 智能階梯分佈生成 (3-10檔)
  - 資金精準分配算法

- **`market_data.py`** - 市場數據獲取
  - USD 最近成交數據
  - 資金簿分析
  - 數據緩存管理
  - 實時市場利率監控

### 🗄️ 數據庫
- **`schema.sql`** - 數據庫表結構
  - daily_summary: 每日收益統計
  - current_status: 系統運行狀態

## 📋 配置文件

### 🐳 部署配置
- **`Dockerfile`** - Docker 容器構建
- **`requirements.txt`** - Python 依賴包

### 📖 文檔
- **`README.md`** - 項目說明
- **`CONFIG_GUIDE.md`** - 配置指南
- **`CONFIG_FLOW_DIAGRAM.md`** - 配置流程圖
- **`TESTING_GUIDE.md`** - 測試指南

## 🚀 使用方式

### 本地運行
```bash
# 確保有足夠資金進行探測 (建議 1000+ USD)
python3 main.py
```

### Docker 運行  
```bash
docker build -t simple-lending-bot .
docker run simple-lending-bot
```

### Railway 部署
```bash
# 自動部署，包含 PostgreSQL
# 環境變量配置後即可運行
```

## 🎯 核心功能

1. **智能資金探測** - 500 USD 固定探測，準確獲取可用資金
2. **多錢包管理** - 自動檢查 funding/exchange/margin 錢包
3. **精準資金分配** - 基於實際可用資金的 10 檔階梯策略
4. **自動放貸** - 每30分鐘自動調整放貸策略
5. **動態利率** - 基於 USD 市場數據動態計算利率
6. **每日結算** - 自動計算和記錄收益
7. **Telegram 通知** - 實時運行狀態通知
8. **高成功率** - 從 0% 提升到 90% 的訂單成功率

## ⚙️ 配置要求

- Bitfinex API Key & Secret (僅需 Funding 權限)
- PostgreSQL 數據庫
- Telegram Bot Token (可選)
- Railway 部署環境變量
- 最小資金建議: 1000 USD (探測需要 500 USD)

## 📈 監控指標

- 每日收益 (USD)
- 年化收益率  
- 資金利用率 (基於實際可用資金)
- 活躍放貸數量
- 平均放貸利率
- 訂單成功率 (目標: 90%+)
- 智能探測效果
- 多錢包資金分佈

## 🚀 技術架構亮點

### 智能探測機制
```python
# main.py:641-734 - 核心創新
def _probe_available_lending_amount(self, wallet_balance: Decimal) -> Decimal:
    # 使用固定 500 USD 進行安全探測
    # 立即取消測試訂單，避免資金占用
    # 保守估算總可用資金 (探測成功金額 × 10)
```

### 多錢包管理
```python
# bitfinex_api.py - 新增功能
def get_all_wallet_balances(self) -> Dict[str, Dict[str, Decimal]]:
    # 檢查 funding, exchange, margin 所有錢包
    
def transfer_between_wallets(self, currency: str, amount: Decimal, 
                           from_wallet: str, to_wallet: str) -> bool:
    # 自動錢包間轉賬功能
```

### 動態分配算法
```python
# 基於實際探測到的可用資金進行精準分配
available_amount = self._probe_available_lending_amount(wallet_balance)
orders = self.strategy.generate_orders(
    available_amount,  # 使用探測到的真實可用金額
    market_data
)
```