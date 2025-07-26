# 專案架構解析 (PROJECT_ARCHITECTURE.md)

## 1. 專案概覽

本專案是一個針對 Bitfinex 平台的自動化資金借貸機器人。它採用了模組化和策略驅動的設計，旨在根據用戶配置的策略和實時市場數據，自動化執行資金借貸操作以優化收益。專案整合了資料庫來記錄市場日誌和收益，並提供了靈活的擴展性。

## 2. 專案結構

```
/BitfinexLendingBot
├── .env                      # Environment variables (API keys, database, etc.)
├── .gitignore                # Git ignore file
├── README.md                 # Project overview and setup guide
├── requirements.txt          # Python dependencies
├── docs/
│   ├── GEMINI_DEVELOPER_GUIDELINES.md # Guidelines for AI development
│   ├── PROJECT_ARCHITECTURE.md # This file
│   ├── COMMANDS.md           # Common commands
│   ├── TOKEN_SYMBOLS.md      # Reference for funding token symbols
│   └── archive/              # Old documentation
├── src/
│   ├── main/
│   │   ├── python/
│   │   │   ├── main.py       # Main application entry point
│   │   │   ├── api/          # (Reserved) API client extensions
│   │   │   ├── core/         # Core logic and framework
│   │   │   │   ├── config.py # Configuration management
│   │   │   │   ├── exceptions.py # Custom exceptions
│   │   │   │   └── strategies/ # Lending strategies
│   │   │   ├── models/       # Pydantic data models
│   │   │   ├── repositories/ # Database interaction layer
│   │   │   └── services/     # Business logic services
│   └── test/
│       ├── integration/      # Integration tests
│       └── unit/             # Unit tests
├── tools/
│   ├── init_db.py            # Database initialization script
│   ├── run_all_tests.py      # Test runner script
│   └── ...                   # Other utility scripts
└── venv/                     # Python virtual environment
```

## 3. 核心組件與數據流

### 3.1 `main.py` - 機器人主程式

`main.py` 是整個機器人的啟動和協調中心。其主要職責包括：
1.  **加載配置:** 通過 `core.config.get_config_manager` 從 `.env` 文件安全地加載並驗證所有配置。
2.  **初始化服務:** 創建 `bfxapi.Client` 用於 API 交互，並初始化 `services.database_manager.DatabaseManager` 來管理資料庫連接池。
3.  **動態加載策略:** 根據 `.env` 中 `STRATEGY_NAME` 的配置，從 `core.strategies` 目錄動態導入並實例化對應的策略類。
4.  **主執行循環:**
    *   定期取消所有現有的資金訂單以應用新策略。
    *   獲取錢包可用餘額。
    *   調用當前策略的 `analyze_and_log_market` 方法分析市場並將數據存入資料庫。
    *   如果餘額充足，調用策略的 `generate_offers` 方法生成新的訂單列表。
    *   執行下單 (`place_funding_offer`)，並將訂單資訊記錄到資料庫。
    *   按預設間隔 (`CHECK_INTERVAL_SECONDS`) 休眠。

### 3.2 `core/config.py` - 配置管理器

`ConfigManager` 使用 `dataclasses` 和 `python-decouple` 庫提供了一個類型安全、結構化的配置管理方案。它將 `.env` 中的變數解析為 `AppConfig` 對象，該對象包含了 `DatabaseConfig`, `ApiConfig`, `TradingConfig`, `StrategyConfig` 和 `LoggingConfig` 等多個子配置，使得配置在整個應用中傳遞和使用時清晰且不易出錯。

### 3.3 `services/database_manager.py` - 資料庫管理器

`DatabaseManager` 負責管理與 PostgreSQL 資料庫的連接。它使用 `psycopg2.pool` 實現了線程安全的連接池，提高了性能和可靠性。它提供了事務支持和統一的查詢執行接口，並封裝了錯誤處理邏輯。

### 3.4 `repositories/` - 資料庫倉庫

倉庫層 (`repositories`) 負責將應用程式的數據模型 (`models`) 與資料庫進行交互。例如，`MarketLogRepository` 提供了將市場分析結果 (`MarketLog` 對象) 存儲到 `market_logs` 表的方法。這種分層將業務邏輯與數據持久化細節分離。

目前的倉庫包括:
*   `daily_profit_repository.py`
*   `interest_payment_repository.py`
*   `market_log_repository.py`

### 3.5 `core/strategies/` - 策略模式

這是機器人決策的核心。
*   **`base_strategy.py`:** 定義了所有策略都必須實現的抽象基類 `BaseStrategy`，包含 `generate_offers` 和 `analyze_and_log_market` 等核心接口。
*   **策略實現:**
    *   `laddering_strategy.py`: 階梯式掛單策略。
    *   `adaptive_laddering_strategy.py`: 根據市場波動性自適應調整的階梯策略。
    *   `spread_filler_strategy.py`: 在買賣價差之間填充訂單的策略。
    *   `market_taker_strategy.py`: 以市場最優買價立即成交的策略。

機器人可以通過修改 `.env` 文件中的 `STRATEGY_NAME` 來無縫切換這些策略，無需改動任何程式碼。

## 4. 配置 (`.env`)

`.env` 文件是機器人所有可配置參數的唯一來源。它取代了舊的 `config.ini`，並通過 `ConfigManager` 進行加載。其內容涵蓋了 API 憑證、資料庫連接資訊、交易參數（如幣種、最小利率）以及策略特定參數（如階梯數量、價差）。

## 5. 測試架構

專案的測試策略已演進為使用 `tools/run_all_tests.py` 腳本來統一執行。
*   **單元測試 (`src/test/unit/`):** 專注於測試單個模組，如 `test_config_manager.py` 用於驗證配置加載和解析的正確性。這些測試不依賴外部服務。
*   **集成測試 (`src/test/integration/`):** 用於測試機器人與 Bitfinex API 的實際交互。
*   **測試運行器 (`tools/run_all_tests.py`):** 提供了一個命令行介面，允許開發者選擇性地運行不同類型的測試，例如可以只運行安全的單元測試，或者運行包含真實交易的完整測試套件，大大提高了測試的靈活性和安全性。

## 6. 資料庫初始化

使用 `tools/init_db.py` 腳本來初始化資料庫。該腳本會連接到 `.env` 文件中配置的資料庫，並創建所有必要的表結構，如 `market_logs`。