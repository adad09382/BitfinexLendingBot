# 多階段構建 - 成本優化的 Python 映像
FROM python:3.9-slim as base

# 設置工作目錄
WORKDIR /app

# 設置環境變量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安裝系統依賴 (最小化)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 構建階段
FROM base as builder

# 複製依賴文件
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir --user -r requirements.txt

# 生產階段
FROM base as production

# 創建非 root 用戶
RUN groupadd -r bitfinex && useradd -r -g bitfinex bitfinex

# 複製安裝的包
COPY --from=builder /root/.local /home/bitfinex/.local

# 確保腳本在 PATH 中
ENV PATH=/home/bitfinex/.local/bin:$PATH

# 複製應用代碼
COPY src/ /app/src/
COPY scripts/ /app/scripts/
COPY config/ /app/config/

# 創建必要的目錄
RUN mkdir -p /app/logs /app/backups /app/data && \
    chown -R bitfinex:bitfinex /app

# 切換到非 root 用戶
USER bitfinex

# 健康檢查腳本
COPY --chown=bitfinex:bitfinex scripts/health_check.py /app/health_check.py
RUN chmod +x /app/health_check.py

# 暴露端口 (用於健康檢查)
EXPOSE 8000

# 設置健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD python3 /app/health_check.py

# 啟動命令
CMD ["python3", "-m", "src.main.python.main"]