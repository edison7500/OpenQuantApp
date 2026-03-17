FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# 1. 利用 uv 的缓存机制，先只复制依赖文件
COPY pyproject.toml uv.lock ./

# 2. 同步环境 (uv 会自动处理虚拟环境)
RUN uv sync --frozen --no-cache

# 3. 复制剩余代码
COPY . .

# 4. 创建一个 .env 文件
RUN touch .env

# 暴露端口
EXPOSE 8501

# 使用 uv run 启动，确保在虚拟环境中运行
CMD ["uv", "run", "streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
