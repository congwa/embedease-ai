# 按本次 SFO 发布授权构建 Linux 运行镜像。
FROM python:3.13-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
COPY packages ./packages
RUN uv sync --frozen --no-dev
RUN .venv/bin/playwright install --with-deps chromium && rm -rf /var/lib/apt/lists/*
COPY app ./app
RUN mkdir -p /app/data /app/logs
EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
