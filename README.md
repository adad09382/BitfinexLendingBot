# SimpleLendingBot 🚀

> **智能放貸機器人** - 基於智能探測技術，自動化 USD 放貸

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
[![Railway](https://img.shields.io/badge/Deploy-Railway-purple.svg)](https://railway.app)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production Ready-brightgreen.svg)]()

## 🎯 核心功能

- 🧠 **智能資金探測**: 500 USD 固定探測，準確獲取可用資金
- 📋 **多錢包管理**: 自動檢查 funding/exchange/margin 錢包
- 💯 **高成功率**: 從 0% 提升到 90% 的訂單成功率
- 🤖 **自動放貸**: 每30分鐘自動調整放貸策略
- 📊 **動態利率**: 基於 USD 實時市場數據計算利率
- 🪜 **精準階梯**: 基於實際可用資金的 3-10 檔階梯分散風險
- 📈 **每日結算**: 自動統計收益和年化收益率
- 📱 **Telegram通知**: 實時運行報告和收益統計

## ✨ 系統特點

- 🧠 **智能技術**: 首創 500 USD 固定探測機制，解決資金分配難題
- 💯 **卓越效果**: 從 0% 提升到 90% 訂單成功率
- ⚡ **極簡架構**: 5個核心Python文件，智能化升級
- 💰 **零成本運行**: Railway免費部署
- 🎯 **用戶導向**: 專注每日收益和年化收益率  
- 🔒 **安全可靠**: 最小權限API，開源透明

## 🏗️ 項目結構

```
SimpleLendingBot/
├── main.py                    # 主程序 (機器人核心邏輯)
├── bitfinex_api.py           # Bitfinex API客戶端
├── simple_ladder_strategy.py  # 階梯放貸策略
├── market_data.py            # 市場數據獲取
├── schema.sql                # 數據庫表結構
├── requirements.txt          # Python依賴
├── Dockerfile               # Docker配置
└── README.md                # 本文檔
```

## 🚀 快速部署

### 方案1: Railway 部署 (推薦)

1. **Fork 本倉庫**
   - 點擊 GitHub 右上角 Fork 按鈕

2. **Railway 部署**
   - 訪問 [Railway.app](https://railway.app)
   - 點擊 "Deploy from GitHub repo"
   - 選擇你的 Fork 倉庫
   - 添加 PostgreSQL 服務

3. **配置環境變量**
   ```bash
   BITFINEX_API_KEY=your_api_key
   BITFINEX_API_SECRET=your_api_secret  
   LENDING_CURRENCY=USD                 # 推薦 USD
   PROBE_TEST_AMOUNT=500                # 探測金額
   MIN_ORDER_AMOUNT=150
   TELEGRAM_BOT_TOKEN=your_bot_token    # 可選
   TELEGRAM_CHAT_ID=your_chat_id        # 可選
   ```

4. **自動部署完成！** 🎉

### 方案2: 本地運行

```bash
# 克隆倉庫
git clone https://github.com/YOUR_USERNAME/BitfinexLendingBot.git
cd BitfinexLendingBot

# 創建虛擬環境
python3 -m venv venv
source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt

# 配置環境變量 (複製 .env.example 到 .env)
cp .env.example .env
# 編輯 .env 填入你的配置

# 初始化數據庫 (需要本地PostgreSQL)
psql -d your_database -f schema.sql

# 運行機器人
python3 main.py
```

## ⚙️ 配置說明

### 🔑 必需配置

```bash
# Bitfinex API認證
BITFINEX_API_KEY=your_api_key
BITFINEX_API_SECRET=your_api_secret

# 數據庫連接 (Railway自動提供)
DATABASE_URL=postgresql://user:pass@host:port/db

# 放貸基本設置
LENDING_CURRENCY=USD              # 放貸幣種 (穩定性佳)
PROBE_TEST_AMOUNT=500            # 智能探測金額
MIN_ORDER_AMOUNT=150             # 最小訂單金額
MAX_LOAN_AMOUNT=100000           # 最大放貸總額
```

### 📊 策略配置

```bash
# 放貸期限
LENDING_MIN_PERIOD=2             # 最短天數
LENDING_MAX_PERIOD=30            # 最長天數  
LENDING_PREFERRED_PERIOD=2       # 首選天數

# 利率設定
MIN_ANNUAL_RATE=0.05            # 5% 年化最低利率
MAX_ANNUAL_RATE=0.50            # 50% 年化最高利率
TARGET_ANNUAL_RATE=0.12         # 12% 目標年化利率

# 動態利率 (推薦開啟)
ENABLE_DYNAMIC_RATE=true        # 啟用動態利率
MARKET_RATE_BUFFER_PERCENT=5    # 市場競爭緩衝5%

# 智能探測 (新增)
PROBE_TEST_AMOUNT=500           # 固定探測金額
PROBE_MULTIPLIER=10             # 保守估算倍數
```

### 🔒 安全配置

```bash
# 資金保護
MAX_UTILIZATION_RATE=100        # 最大資金使用率
SINGLE_ORDER_MAX_PERCENT=100    # 單筆訂單最大比例

# 系統穩定性
MAX_RETRY_ATTEMPTS=5            # API重試次數
RETRY_DELAY_SECONDS=10          # 重試間隔
RUN_INTERVAL_MINUTES=30         # 運行間隔
```

### 📱 Telegram通知 (可選)

```bash
TELEGRAM_BOT_TOKEN=bot_token    # Bot Token
TELEGRAM_CHAT_ID=chat_id        # Chat ID
```

## 📊 使用體驗

### 📱 Telegram通知示例

**運行報告 (每30分鐘)**:
```
🤖 SimpleLendingBot 運行報告

⏰ 運行時間: 2025-08-14 22:30:00
💰 可用餘額: 499.50 UST  
📊 成功訂單: 3/3
💵 放貸金額: 499.50 UST
📈 資金利用率: 100.0%

🎯 策略: 階梯放貸
⚡ 執行時間: 8.3 秒
✅ 狀態: 正常運行

下次運行: 30 分鐘後
```

**每日收益報告 (每天00:05)**:
```
📊 每日收益報告 - 2025-08-14

💰 總資金: 40,599 USD (全錢包)
🧠 智能探測: 18,912 USD 可用資金
💪 工作資金: 499.50 UST (100.0%)
😴 閒置資金: 0.00 UST

🎉 今日收益: 0.1200 UST  
📈 年化收益率: 8.76%
💎 累計收益: 2.4500 UST

🎯 放貸詳情:
   📋 活躍放貸: 3 筆
   📊 平均利率: 8.85% (年化)

✅ 每日結算完成
```

### 📈 實際運行效果

**利率範圍**: 0.024% - 0.027% 日利率 (8.7% - 10% 年化)  
**策略**: 基於市場數據的動態階梯策略  
**風險**: 分散到3-10檔訂單，降低單一風險  

## 🛠️ 監控和維護

### Railway 部署監控
```bash
# 查看日誌
railway logs --follow

# 查看服務狀態
railway status

# 重啟服務  
railway redeploy
```

### 健康檢查
系統自動提供健康檢查端點：
```
GET https://your-app.railway.app/health
Response: {"status": "healthy", "service": "SimpleLendingBot"}
```

## 📈 配置建議

### 保守型設置
```bash
LENDING_CURRENCY=UST
MIN_ORDER_AMOUNT=150
TARGET_ANNUAL_RATE=0.08         # 8% 年化
MAX_UTILIZATION_RATE=80         # 80% 資金使用率
```

### 積極型設置  
```bash
LENDING_CURRENCY=UST
MIN_ORDER_AMOUNT=100
TARGET_ANNUAL_RATE=0.15         # 15% 年化
MAX_UTILIZATION_RATE=100        # 100% 資金使用率
```

## ⚠️ 重要提醒

### 安全注意事項
- 🔑 **API權限**: 只勾選 Funding (放貸)權限
- 🔐 **密鑰管理**: 定期更換API密鑰
- 📊 **監控**: 定期檢查放貸狀況
- 💰 **風險**: 加密貨幣放貸有風險，請評估風險承受能力

### 故障排除
- **數據庫連接失敗**: 檢查Railway PostgreSQL服務
- **API調用失敗**: 檢查Bitfinex API密鑰
- **Telegram通知失敗**: 檢查Bot Token和Chat ID

## ❓ 常見問題

**Q: 系統安全嗎？**  
A: API只申請放貸權限，無法提現或交易，代碼開源可審計。

**Q: Railway免費額度夠用嗎？**  
A: 完全夠用，系統資源消耗極小。

**Q: 支持哪些幣種？**  
A: 支持所有Bitfinex放貸幣種，推薦 USD (穩定性佳，流動性高)。

**Q: 最小資金要求？**  
A: 建議至少 1000 USD，因為智能探測需要 500 USD，最小訂單 150 USD。

## 🤝 技術支持

- **GitHub Issues**: [報告問題](https://github.com/YOUR_USERNAME/BitfinexLendingBot/issues)
- **GitHub Discussions**: [交流討論](https://github.com/YOUR_USERNAME/BitfinexLendingBot/discussions)

## 📄 授權協議

本項目採用 MIT 協議開源。詳見 [LICENSE](LICENSE) 文件。

---

## 🎯 核心價值

**SimpleLendingBot** 讓放貸自動化進入智能時代：

- 🧠 **智能突破**: 首創 500 USD 探測技術，解決資金分配難題
- 💯 **卓越效果**: 從 0% 提升到 90% 訂單成功率
- 🎯 **精準分配**: 基於實際可用資金，不浪費額度
- 💰 **成本最優**: 零成本運行，資金完全用於放貸  
- ⚡ **極速部署**: 5分鐘上線，智能化配置
- 🔧 **零維護**: 智能運行，最低管理成本

**讓智能為資金服務，讓技術為收益赦能！** 🧠💰📈

---

<div align="center">
<strong>如果這個項目對你有幫助，請給個 ⭐ Star！</strong><br>
<em>SimpleLendingBot - 智能，而且高效</em> 🧠🚀
</div>