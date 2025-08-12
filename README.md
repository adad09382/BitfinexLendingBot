# SimpleLendingBot 🚀

> **極簡版放貸機器人** - 專注核心功能，成本最低，Railway 免費部署

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
[![Railway](https://img.shields.io/badge/Deploy-Railway-purple.svg)](https://railway.app)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production Ready-brightgreen.svg)]()

## 🎯 設計理念

**用戶真正關心的只有兩件事：**
- 💰 **每日收益多少？**
- 📈 **年化收益率多少？**

**因此我們極簡化系統：**
- 🗂️ 從 50+ 文件精簡到 6 個文件  
- 📊 從 10+ 數據表精簡到 2 張表
- 💸 從 $45+/月降到 $0/月 (Railway 免費)
- ⚡ 從 2-3小時部署到 5分鐘部署

## ✨ 核心特性

- 🚀 **超簡架構**: 單一 Python 腳本 (~400行)
- 💰 **零成本運行**: Railway 免費部署
- 📊 **用戶導向**: 專注每日收益和年化收益率  
- 🎯 **智能策略**: 5階梯自動放貸
- 📱 **Telegram 通知**: 實時運行報告
- ⚡ **5分鐘部署**: Git push 自動上線

## 📊 vs 企業版對比

| 項目 | 企業版 (main分支) | 精簡版 (simple分支) |
|------|------------------|---------------------|
| **文件數量** | 50+ 文件 | 6 文件 |
| **代碼量** | 7,850+ 行 | ~400 行 |
| **數據表** | 10+ 張表 | 2 張表 |
| **依賴包** | 30+ 依賴 | 4 個依賴 |
| **部署方式** | Docker Compose | 單容器 |
| **月成本** | $45+ | **$0** |
| **部署時間** | 2-3 小時 | **5 分鐘** |
| **維護難度** | 高 | **極低** |

## 🏗️ 系統架構

### 📋 文件結構
```
SimpleLendingBot/
├── main.py           # 400行主腳本 (包含所有邏輯)
├── requirements.txt  # 4個核心依賴
├── schema.sql        # 2張數據表結構  
├── .env.example     # 配置模板
├── Dockerfile       # 單容器部署
└── README.md        # 本文檔
```

### 🗄️ 數據庫設計 (2張表)
```sql
daily_summary      -- 每日總結 (用戶最關心)
├── date          -- 日期 (主鍵)
├── total_balance -- 總資金 💰
├── working_balance -- 放貸中資金 💪  
├── daily_earnings -- 今日收益 🎉
├── annual_rate   -- 年化收益率 📈
└── utilization_rate -- 資金利用率

current_status     -- 實時狀態 (系統監控)  
├── total_available -- 可用資金
├── active_offers_count -- 當前訂單數
├── last_update   -- 最後更新
└── system_status -- 運行狀態
```

### 🎯 運行邏輯 (30分鐘循環)
```
1. 取消舊訂單 → 2. 獲取餘額 → 3. 執行5階梯策略 → 
4. 提交新訂單 → 5. 更新狀態 → 6. 發送 Telegram 通知
```

## 🚀 快速部署 (5分鐘上線)

### 方案1: Railway 部署 (推薦)

1. **Fork 本倉庫**
   ```bash
   # 點擊 GitHub 右上角 Fork 按鈕
   ```

2. **Railway 部署**
   - 訪問 [Railway.app](https://railway.app)
   - 點擊 "Deploy from GitHub repo"
   - 選擇你的 Fork 倉庫
   - **重要**: 選擇 `simple` 分支
   - 添加 PostgreSQL 服務

3. **配置環境變量**
   ```bash
   BITFINEX_API_KEY=your_api_key
   BITFINEX_API_SECRET=your_api_secret  
   LENDING_CURRENCY=USD
   MIN_ORDER_AMOUNT=50
   TELEGRAM_BOT_TOKEN=your_bot_token    # 可選
   TELEGRAM_CHAT_ID=your_chat_id        # 可選
   ```

4. **自動部署完成！** 🎉

### 方案2: 本地測試

```bash
# 克隆倉庫 (simple 分支)
git clone -b simple https://github.com/YOUR_USERNAME/BitfinexLendingBot.git
cd BitfinexLendingBot

# 安裝依賴
pip install -r requirements.txt

# 配置環境
cp .env.example .env
# 編輯 .env 填入你的 API 密鑰

# 初始化數據庫 (本地 PostgreSQL)
psql -d your_database -f schema.sql

# 運行機器人
python main.py
```

## ⚙️ 配置說明

### 🔑 Bitfinex API 設置

1. 登入 [Bitfinex](https://www.bitfinex.com)
2. 前往 **Settings** → **API** → **Create New Key**
3. **權限設置**: 只勾選 **Funding** (放貸功能)
4. 複製 **Key** 和 **Secret** 到環境變量

### 📱 Telegram 通知設置 (可選但推薦)

1. **創建機器人**:
   - 聯繫 [@BotFather](https://t.me/BotFather)
   - 發送 `/newbot` 創建機器人
   - 獲得 **Bot Token**

2. **獲取 Chat ID**:
   - 給你的機器人發送一條消息
   - 訪問: `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - 找到 `"chat":{"id": 數字}`

### 💰 交易參數建議

```bash
LENDING_CURRENCY=USD              # 建議 USD (流動性最好)
MIN_ORDER_AMOUNT=50              # 最小訂單 50 USD
MAX_LOAN_AMOUNT=10000           # 根據資金量調整  
RUN_INTERVAL_MINUTES=30         # 建議 30 分鐘間隔
```

## 📊 使用體驗

### 📱 Telegram 通知示例

**運行報告 (每30分鐘)**:
```
🤖 SimpleLendingBot 運行報告

⏰ 運行時間: 2025-01-15 14:30:00
💰 可用餘額: 5,000.00 USD  
📊 成功訂單: 5/5
💵 放貸金額: 4,750.00 USD
📈 資金利用率: 95.0%

🎯 策略: 5階梯放貸
✅ 狀態: 正常運行
```

**每日收益報告 (每天00:05)**:
```
📊 每日收益報告 - 2025-01-15

💰 總資金: 10,000.00 USD
💪 工作資金: 9,500.00 USD (95.0%)
😴 閒置資金: 500.00 USD

🎉 今日收益: 2.47 USD  
📈 年化收益率: 9.01%
💎 累計收益: 127.83 USD

🎯 放貸詳情:
   📋 活躍放貸: 5 筆
   📊 平均利率: 9.12% (年化)

✅ 每日結算完成
```

### 📈 數據查詢

```sql
-- 查看最近7天收益
SELECT * FROM daily_summary 
ORDER BY date DESC LIMIT 7;

-- 查看收益統計
SELECT 
    ROUND(AVG(daily_earnings), 4) as avg_daily_earnings,
    ROUND(AVG(annual_rate) * 100, 2) as avg_annual_rate_percent
FROM daily_summary 
WHERE date >= CURRENT_DATE - INTERVAL '30 days';

-- 查看當前狀態  
SELECT * FROM current_status;
```

## 🛠️ 監控和維護

### 📊 Railway 監控

```bash
# 查看日誌
railway logs --follow

# 查看服務狀態
railway status

# 重啟服務
railway redeploy
```

### 🔍 健康檢查

Railway 自動提供健康檢查端點：
```
GET https://your-app.railway.app/health
Response: {"status": "healthy", "service": "SimpleLendingBot"}
```

### ⚠️ 故障排除

**常見問題**:

1. **數據庫連接失敗**
   ```
   ERROR - 數據庫連接失敗
   解決: 檢查 Railway PostgreSQL 服務狀態
   ```

2. **API 調用失敗**
   ```  
   ERROR - 獲取餘額失敗
   解決: 檢查 Bitfinex API 密鑰和網絡
   ```

3. **Telegram 通知失敗**
   ```
   WARNING - Telegram 通知發送失敗  
   解決: 檢查 BOT_TOKEN 和 CHAT_ID
   ```

**緊急停止**:
```bash
# Railway 停止服務
railway service pause

# 本地停止  
Ctrl+C
```

## 📈 升級路線

### 🎯 當前版本 (Simple v1.0)
- ✅ 核心放貸功能
- ✅ 每日收益統計  
- ✅ Telegram 通知
- ✅ Railway 免費部署

### 🚀 未來版本規劃

**v2.0 - 增強版** (需要時):
- 📊 多策略支持
- 📈 高級監控告警
- 📱 更豐富的通知內容

**v3.0 - Web 版** (按需開發):  
- 🌐 Web Dashboard
- 📊 圖表可視化
- ⚙️ 在線配置管理

**企業版** (切換到 main 分支):
- 🏢 完整企業級功能
- 🔧 高級風險管理  
- 📈 完整監控系統

## ❓ 常見問題

**Q: 為什麼選擇精簡版？**  
A: 用戶只關心每日收益和年化收益率，企業版功能過於複雜且成本高。

**Q: 安全性如何？**
A: API 密鑰加密存儲，只申請最小權限 (Funding)，代碼開源可審計。

**Q: Railway 免費額度夠用嗎？**
A: 完全夠用！精簡版資源消耗極小，月成本 $0。

**Q: 如何切換到企業版？**  
A: `git checkout main` 即可切換到功能完整的企業版。

**Q: 支持哪些幣種？**
A: 支持所有 Bitfinex 放貸幣種，建議使用 USD (流動性最佳)。

**Q: 最小資金要求？**
A: 建議至少 500 USD，最小訂單 50 USD。

## 🤝 社區支持

- **GitHub Issues**: [報告問題](https://github.com/YOUR_USERNAME/BitfinexLendingBot/issues)
- **GitHub Discussions**: [交流討論](https://github.com/YOUR_USERNAME/BitfinexLendingBot/discussions)  
- **企業版**: 切換到 `main` 分支

## 📄 授權協議

本項目採用 MIT 協議開源。請查看 [LICENSE](LICENSE) 文件了解詳情。

---

## 🎯 核心價值

**SimpleLendingBot** 的核心價值就是讓放貸機器人回歸簡單：

- 🎯 **專注用戶價值**: 只關心每日收益和年化收益率
- 💰 **成本最優**: 零成本運行，資金完全用於放貸
- ⚡ **極速部署**: 5分鐘上線，無需複雜配置  
- 🔧 **零維護**: 自動運行，minimal 管理成本

**讓賺錢變簡單，讓技術為收益服務！** 💰📈

---

<div align="center">
<strong>如果這個項目對你有幫助，請給個 ⭐ Star！</strong><br>
<em>SimpleLendingBot - 極簡，但不簡陋</em> 🚀
</div>
