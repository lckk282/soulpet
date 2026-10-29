FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SOULPET_HOME=/app/data

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY launcher ./launcher
COPY frontend/dist ./frontend/dist

# 数据与配置放卷里，便于备份与升级
VOLUME ["/app/data", "/app/config"]

EXPOSE 8787

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8787/healthz')" || exit 1

CMD ["python", "launcher/launcher.py", "--host", "127.0.0.1", "--port", "8787", "--no-browser"]
