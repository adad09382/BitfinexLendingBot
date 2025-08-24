# SimpleLendingBot 配置指南 ⚙️

> **智能放貸配置說明** - 基於智能探測和多錢包管理的核心配置參數

## 🔑 必需配置

### API 認證
```bash
# Bitfinex API 認證 (必須)
BITFINEX_API_KEY=your_api_key
BITFINEX_API_SECRET=your_api_secret

# 數據庫連接 (Railway 自動提供)
DATABASE_URL=postgresql://user:pass@host:port/db
```

**⚠️ 重要提醒：**
- API權限只勾選 **Funding (放貸功能)**
- 絕對不要給予 Trading、Withdrawal 權限

## 💰 放貸參數

### 基本設置
```bash
# 放貸幣種
LENDING_CURRENCY=USD              # 推薦 USD (穩定性佳，流動性高)

# 金額控制
MIN_ORDER_AMOUNT=150             # 單筆最小金額
MAX_LOAN_AMOUNT=100000           # 總放貸上限

# 期限控制  
LENDING_MIN_PERIOD=2             # 最短天數
LENDING_MAX_PERIOD=30            # 最長天數
LENDING_PREFERRED_PERIOD=2       # 首選天數
```

### 利率設定
```bash
# 利率邊界
MIN_ANNUAL_RATE=0.05            # 5% 年化最低利率
MAX_ANNUAL_RATE=0.50            # 50% 年化最高利率  
TARGET_ANNUAL_RATE=0.12         # 12% 目標年化利率

# 動態利率 (推薦開啟)
ENABLE_DYNAMIC_RATE=true        # 啟用動態利率
MARKET_RATE_BUFFER_PERCENT=5    # 市場競爭緩衝 5%
MIN_RATE_SAFETY_MARGIN=0.02     # 最低利率安全邊際 2%

# 智能資金探測 (新增)
PROBE_TEST_AMOUNT=500           # 固定探測金額 500 USD
PROBE_MULTIPLIER=10             # 保守估算倍數 (探測金額 × 10)
```

### 資金保護
```bash
# 資金使用控制
MAX_UTILIZATION_RATE=100        # 最大資金使用率 100%
SINGLE_ORDER_MAX_PERCENT=100    # 單筆訂單最大比例 100%

# 系統穩定性
MAX_RETRY_ATTEMPTS=5            # API 重試次數
RETRY_DELAY_SECONDS=10          # 重試間隔 (秒)
ORDER_TIMEOUT_SECONDS=30        # 請求超時 (秒)
RUN_INTERVAL_MINUTES=30         # 運行間隔 (分鐘)
```

## 📱 可選配置

### Telegram 通知
```bash
# Telegram 機器人 (可選但推薦)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

**設置步驟：**
1. 聯繫 [@BotFather](https://t.me/BotFather) 創建機器人
2. 發送 `/newbot` 獲得 Token
3. 給機器人發消息，訪問 `https://api.telegram.org/bot<TOKEN>/getUpdates` 獲取 Chat ID

## 🎯 配置實例

### 保守型 (適合新手)
```bash
LENDING_CURRENCY=USD
MIN_ORDER_AMOUNT=150
MAX_LOAN_AMOUNT=1000
TARGET_ANNUAL_RATE=0.08         # 8% 年化
MAX_UTILIZATION_RATE=80         # 80% 資金使用率
LENDING_PREFERRED_PERIOD=7      # 7天期限
PROBE_TEST_AMOUNT=500           # 探測金額
```

### 積極型 (適合有經驗用戶)
```bash
LENDING_CURRENCY=USD
MIN_ORDER_AMOUNT=100  
MAX_LOAN_AMOUNT=50000
TARGET_ANNUAL_RATE=0.15         # 15% 年化
MAX_UTILIZATION_RATE=100        # 100% 資金使用率
LENDING_PREFERRED_PERIOD=2      # 2天期限
PROBE_TEST_AMOUNT=500           # 探測金額
```

## 🧠 智能資金探測機制

### 技術突破
**問題解決**: 解決了傳統方式無法準確獲取實際可用放貸資金的問題
- **舊方式**: 使用錢包總餘額 ÷ 10，導致 0% 成功率
- **新方式**: 智能探測實際可用資金，達到 90% 成功率

### 探測流程
1. **多錢包檢查**: 自動檢查 funding、exchange、margin 錢包
2. **智能探測**: 使用固定 500 USD 進行測試放貸
3. **即時取消**: 立即取消測試訂單，避免資金占用
4. **保守估算**: 探測成功金額 × 10 倍作為可用資金
5. **動態分配**: 將實際可用資金分成 10 檔階梯
6. **自動轉賬**: 必要時自動從其他錢包轉入資金

### 實際效果
- **成功率**: 從 0% 提升到 90% (9/10 訂單)
- **資金利用**: 基於實際可用資金，不浪費額度
- **風險控制**: 固定 500 USD 探測，低風險

## 📊 動態利率機制

### 運作原理
1. **市場數據獲取**: 自動獲取 USD 最近成交和競爭對手數據
2. **智能計算**: 60% 競爭對手利率 + 40% 最近成交利率
3. **競爭優勢**: 在基準利率基礎上增加 5% 緩衝
4. **階梯分佈**: 基於探測到的實際可用資金生成 3-10 檔階梯利率
5. **風險保護**: 確保利率在設定的安全範圍內

### 實際效果
- **利率範圍**: 通常在 8-12% 年化
- **自動調整**: 每 30 分鐘根據市場變化調整
- **競爭力**: 始終保持市場競爭優勢
- **資金精準**: 基於實際可用資金進行利率計算

## ⚠️ 重要提醒

### 安全注意事項
- 🔑 **API 權限**: 只申請 Funding 權限
- 🔐 **密鑰安全**: 定期更換 API 密鑰  
- 📊 **定期監控**: 通過 Telegram 監控運行狀態
- 💰 **風險管理**: 評估個人風險承受能力

### 配置調整建議
- **市場波動大**: 縮短期限 (2-3天)，提高最低利率
- **市場平穩**: 延長期限 (7-14天)，使用目標利率
- **資金不足**: 降低最小金額，提高資金利用率

## 📈 監控指標

### 關鍵數據
- **日收益率**: 每日實際收益
- **年化收益率**: 基於日收益計算的年化率
- **資金利用率**: 工作資金 / 總資金
- **成交率**: 成功訂單 / 總訂單

### 優化建議
- **成交率低**: 降低目標利率或延長期限
- **收益率低**: 提高目標利率或增加資金利用率
- **風險過高**: 降低單筆比例或分散期限

---

## 🎯 總結

SimpleLendingBot 的配置基於智能技術突破：

1. **智能探測**: 自動探測實際可用放貸資金
2. **精準分配**: 基於真實資金進行 10 檔階梯分配
3. **多錢包管理**: 自動檢查和轉賬不同錢包類型
4. **高成功率**: 從 0% 提升到 90% 的訂單成功率
5. **風險可控**: 固定 500 USD 探測，多重保護機制
6. **靈活部署**: 支持本地和雲端部署

記住：**智能探測讓資金利用更精準，配置更簡單！**

---

<div align="center">
<strong>📖 更多文檔</strong><br>
<a href="README.md">項目介紹</a> • 
<a href="PROJECT_STRUCTURE.md">項目結構</a>
<br><br>
<em>SimpleLendingBot - 讓配置變得簡單專業</em> 🚀
</div>