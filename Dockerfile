# SimpleLendingBot 精簡版 Dockerfile
# 單容器部署，專為 Railway 雲端優化

FROM python:3.11-slim

# 設置標籤信息
LABEL maintainer="BitfinexLendingBot Team"
LABEL version="1.0.0"
LABEL description="SimpleLendingBot - 極簡版放貸機器人"

# 設置工作目錄
WORKDIR /app

# 設置環境變量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# 安裝系統依賴 (最小化)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 複製依賴文件並安裝 Python 包
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 複製應用代碼
COPY main.py .
COPY schema.sql .
COPY .env.example .

# 創建非 root 用戶 (安全最佳實踐)
RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app

# 切換到非 root 用戶
USER botuser

# 健康檢查 (Railway 需要)
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/health || exit 1

# 暴露端口 (Railway 動態分配)
EXPOSE ${PORT:-8080}

# 啟動命令
CMD ["python", "main.py"]