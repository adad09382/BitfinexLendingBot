# BitfinexLendingBot 生產部署指南

## 🚀 快速部署

### 前置需求
- Docker & Docker Compose
- 2GB RAM + 1 vCPU + 20GB SSD 的 VPS
- Bitfinex API 密鑰
- Telegram Bot Token (可選)

### 部署步驟

1. **克隆專案**
```bash
git clone https://github.com/your-username/BitfinexLendingBot.git
cd BitfinexLendingBot
```

2. **配置環境變量**
```bash
cp .env.example .env
nano .env  # 填入實際的 API 密鑰和配置
```

3. **啟動服務**
```bash
# 基本部署 (不包含 Web 介面)
docker-compose up -d

# 包含 Web 介面的完整部署
docker-compose --profile web up -d
```

4. **驗證部署**
```bash
# 檢查服務狀態
docker-compose ps

# 查看日誌
docker-compose logs -f bitfinex-bot

# 健康檢查
curl http://localhost/health
```

## 📊 成本優化配置

### 資源配置
```yaml
# 生產環境資源限制
services:
  bitfinex-bot:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 512M
          cpus: '0.25'
```

### 預期成本
- **VPS (2GB RAM + 1 vCPU)**: $35-45/月
- **存儲 (20GB SSD)**: $5-10/月
- **網絡流量**: $2-5/月
- **總成本**: ~$45/月

## 🔧 配置管理

### 環境變量
| 變量名 | 必需 | 描述 |
|--------|------|------|
| `BITFINEX_API_KEY` | ✅ | Bitfinex API 密鑰 |
| `BITFINEX_API_SECRET` | ✅ | Bitfinex API 秘密 |
| `DB_PASSWORD` | ✅ | 資料庫密碼 |
| `TELEGRAM_BOT_TOKEN` | ❌ | Telegram 通知 Token |
| `TELEGRAM_CHAT_ID` | ❌ | Telegram 聊天 ID |

### 核心配置文件
```
config/
├── app.yaml          # 應用配置
├── database.yaml     # 資料庫配置
├── strategies.yaml   # 交易策略配置
└── logging.yaml      # 日誌配置
```

## 🏥 監控與維護

### 健康檢查
```bash
# 應用健康狀態
docker exec bitfinex-lending-bot python3 /app/health_check.py

# 資料庫狀態
docker exec bitfinex-postgres pg_isready -U bitfinex_user

# 容器狀態
docker-compose ps
```

### 日誌管理
```bash
# 實時日誌
docker-compose logs -f

# 應用日誌
docker exec bitfinex-lending-bot tail -f /app/logs/bot.log

# 資料庫日誌
docker-compose logs postgres
```

### 備份策略
```bash
# 手動備份
docker exec bitfinex-postgres /usr/local/bin/backup_db.sh

# 自動備份 (添加到 cron)
0 2 * * * docker exec bitfinex-postgres /usr/local/bin/backup_db.sh
```

## 🔒 安全配置

### 資料庫安全
- 使用強密碼
- 限制網絡訪問
- 定期備份
- 啟用 SSL 連接

### API 安全
- 安全存儲 API 密鑰
- 使用環境變量
- 定期輪換密鑰
- 監控 API 使用

### 容器安全
```bash
# 非 root 用戶運行
USER bitfinex

# 只讀文件系統
read_only: true

# 安全限制
security_opt:
  - no-new-privileges:true
```

## 📈 性能調優

### 資料庫優化
```sql
-- 定期分析表統計
ANALYZE;

-- 重建索引
REINDEX DATABASE bitfinex_bot;

-- 清理舊數據
DELETE FROM notification_logs WHERE created_at < NOW() - INTERVAL '30 days';
```

### 應用優化
```bash
# 監控內存使用
docker stats bitfinex-lending-bot

# 監控磁盤使用
docker exec bitfinex-lending-bot df -h

# 清理日誌
docker exec bitfinex-lending-bot find /app/logs -name "*.log" -mtime +7 -delete
```

## 🚨 故障排除

### 常見問題

1. **容器無法啟動**
```bash
# 檢查日誌
docker-compose logs bitfinex-bot

# 檢查配置
docker-compose config
```

2. **資料庫連接失敗**
```bash
# 檢查資料庫狀態
docker-compose exec postgres pg_isready

# 重置資料庫
docker-compose down -v
docker-compose up -d
```

3. **API 調用失敗**
```bash
# 檢查 API 密鑰
docker-compose exec bitfinex-bot env | grep BITFINEX

# 測試 API 連接
docker-compose exec bitfinex-bot python3 -c "
from src.main.python.api.bitfinex_api_client import BitfinexApiClient
client = BitfinexApiClient()
print(client.get_wallet_balances())
"
```

### 恢復操作

1. **從備份恢復**
```bash
# 停止服務
docker-compose down

# 恢復資料庫
gunzip < /app/backups/bitfinex_bot_backup_YYYYMMDD_HHMMSS.sql.gz | \
docker exec -i bitfinex-postgres psql -U bitfinex_user -d bitfinex_bot

# 重啟服務
docker-compose up -d
```

2. **重置應用**
```bash
# 完全重置
docker-compose down -v
docker system prune -f
docker-compose up -d
```

## 📋 維護檢查清單

### 每日檢查
- [ ] 檢查應用健康狀態
- [ ] 查看錯誤日誌
- [ ] 驗證每日結算執行
- [ ] 檢查 Telegram 通知

### 每週檢查
- [ ] 檢查磁盤使用率
- [ ] 清理舊日誌文件
- [ ] 驗證備份完整性
- [ ] 檢查容器資源使用

## 📊 監控與告警

### 監控服務部署

啟動包含監控的完整系統：
```bash
# 基本系統 + 監控
docker-compose --profile monitoring up -d

# 完整系統 (包含 Web 介面和監控)
docker-compose --profile web --profile monitoring up -d
```

### 監控功能

1. **系統指標監控**
   - CPU 使用率 (預設閾值: 80%)
   - 記憶體使用率 (預設閾值: 80%)
   - 磁碟使用率 (預設閾值: 90%)
   - Docker 容器健康狀態

2. **業務指標監控**
   - API 響應時間
   - 資料庫連接狀態
   - 放貸訂單成功率
   - 每日結算執行狀態

3. **告警通知**
   - Telegram 實時告警
   - 多級別告警 (info, warning, critical)
   - 告警記錄和追蹤

### 監控配置

在 `.env` 文件中配置告警閾值：
```bash
# 告警閾值配置
ALERT_THRESHOLDS_CPU=80          # CPU 使用率告警閾值 (%)
ALERT_THRESHOLDS_MEMORY=80       # 記憶體使用率告警閾值 (%)
ALERT_THRESHOLDS_DISK=90         # 磁碟使用率告警閾值 (%)
MONITOR_INTERVAL=60              # 監控檢查間隔 (秒)

# Telegram 通知 (必需)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 監控測試

運行監控系統測試：
```bash
# 測試監控功能
python3 scripts/test_monitor.py

# 查看監控日誌
docker-compose logs -f monitor
```

### 監控資料庫查詢

查看監控數據：
```sql
-- 查看最近的告警
SELECT * FROM recent_alerts;

-- 查看系統健康摘要
SELECT * FROM system_health_summary;

-- 查看性能基準
SELECT * FROM performance_baselines;
```

### 監控維護

1. **清理歷史數據**
```sql
-- 執行清理函數 (自動清理 30 天前的數據)
SELECT cleanup_old_monitoring_data();
```

2. **調整告警閾值**
```bash
# 修改環境變量後重啟監控服務
docker-compose restart monitor
```

3. **監控服務故障排除**
```bash
# 檢查監控服務狀態
docker-compose ps monitor

# 查看監控服務日誌
docker-compose logs monitor

# 重啟監控服務
docker-compose restart monitor
```

### 每月檢查
- [ ] 更新 Docker 映像
- [ ] 檢查安全更新
- [ ] 分析性能指標
- [ ] 備份配置文件

## 🔄 更新部署

```bash
# 拉取最新代碼
git pull origin main

# 重建映像
docker-compose build --no-cache

# 平滑重啟
docker-compose up -d

# 驗證更新
docker-compose logs -f bitfinex-bot
```

## 📞 支援

如遇到問題，請：
1. 檢查本文檔的故障排除章節
2. 查看應用日誌獲取詳細錯誤資訊
3. 提交 GitHub Issue 並附上相關日誌

---

**最後更新**: 2025-07-30  
**版本**: 1.0.0  
**支援**: BitfinexLendingBot Team