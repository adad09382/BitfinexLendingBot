# 常用命令參考 (COMMANDS.md)

本文件匯總了 Bitfinex Lending Bot 專案中常用的命令，方便您快速查閱和執行。

## 1. 環境設置與依賴

*   **激活虛擬環境 (macOS/Linux):**
    ```bash
    source venv/bin/activate
    ```
*   **激活虛擬環境 (Windows):**
    ```bash
    .\venv\Scripts\activate
    ```
*   **安裝或更新專案依賴:**
    ```bash
    pip install -r requirements.txt
    ```

## 2. 資料庫初始化

在首次運行機器人之前，您需要初始化資料庫。此命令會根據 `.env` 文件中的配置連接到 PostgreSQL 資料庫並創建所需的表。

*   **運行資料庫初始化腳本:**
    ```bash
    python tools/init_db.py
    ```

## 3. 運行主程式

在運行主程式之前，請確保您已在 `.env` 文件中完整配置了 Bitfinex API 金鑰、資料庫連接以及所有機器人參數 (如策略、幣種等)。

*   **運行 Bitfinex Lending Bot:**
    ```bash
    python src/main/python/main.py
    ```

## 4. 運行測試

專案提供了一個統一的測試腳本 `tools/run_all_tests.py`，可以用於運行不同範圍的測試。直接運行舊的單個測試文件已不再被支持。

**重要提示：** 包含 `--include-trading` 參數的測試將會**真實地在 Bitfinex 平台上進行 API 操作** (如下單、取消訂單)。請務必謹慎，並在生產環境中小心使用。

*   **運行所有最安全的測試 (推薦):**
    *   這將只運行不依賴 API 的單元測試，如配置管理器測試。
    ```bash
    python tools/run_all_tests.py --config-only
    ```

*   **運行所有只讀操作的測試:**
    *   這將包括單元測試和不會修改帳戶狀態的 API 測試 (如獲取餘額、分析市場)。
    ```bash
    python tools/run_all_tests.py --safe-only
    ```

*   **運行包含真實交易的完整測試套件 (請謹慎使用):**
    *   **警告：** 此命令會真實下單和取消訂單。
    ```bash
    python tools/run_all_tests.py --include-trading
    ```

## 5. 其他常用命令

*   **檢查 Python 依賴包:**
    ```bash
    pip freeze
    ```
*   **更新 `requirements.txt` (當您手動安裝了新的依賴時):**
    ```bash
    pip freeze > requirements.txt
    ```
*   **檢查 Git 狀態:**
    ```bash
    git status
    ```
*   **查看 Git 差異:**
    ```bash
    git diff
    ```
*   **查看 Git 日誌:**
    ```bash
    git log
    ```