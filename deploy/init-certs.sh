#!/usr/bin/env bash
# 一次性准备 HTTPS 证书，放在 deploy/certs/ 下供 nginx 使用。
#
#   ./init-certs.sh            # 有 DOMAIN 走 Let's Encrypt，没有就自签
#   ./init-certs.sh --self     # 强制自签（没域名时用这个）
#
# 说明：本项目不替你做 DNS 解析，签证书前请先把域名 A 记录指到这台机器，
# 并且 80 端口能从公网访问（Let's Encrypt 要用它做校验）。
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
mkdir -p certs certbot/www

# 读取 .env（只需要 DOMAIN / EMAIL）
if [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a; . ./.env; set +a
fi

DOMAIN="${DOMAIN:-}"
EMAIL="${EMAIL:-}"
FORCE_SELF=0
case "${1:-}" in
  --self|--self-signed) FORCE_SELF=1 ;;
esac

if [ -f certs/fullchain.pem ] && [ -f certs/privkey.pem ]; then
  echo "[ok] certs/ 里已经有证书，跳过。要重签请先删掉 certs/fullchain.pem 与 certs/privkey.pem"
  exit 0
fi

if [ "$FORCE_SELF" = "0" ] && [ -n "$DOMAIN" ] && [ -n "$EMAIL" ]; then
  echo "[1/2] 向 Let's Encrypt 申请 $DOMAIN 的证书…"
  # 用 standalone 模式临时占 80 端口。此时 nginx 不能占用 80，
  # 所以这个脚本要在 docker compose up 之前跑。
  docker run --rm -p 80:80 \
    -v "$(pwd)/certs:/etc/letsencrypt" \
    certbot/certbot certonly --standalone --non-interactive --agree-tos \
    -m "$EMAIL" -d "$DOMAIN" \
    --cert-name "$DOMAIN" 2>&1 | tail -20 || {
      echo
      echo "[!] 申请失败。常见原因：域名没解析到本机 / 80 端口被占用 / 次数超限。"
      echo "    退回自签证书：./init-certs.sh --self"
      exit 1
    }
  cp "certs/live/${DOMAIN}/fullchain.pem" "certs/live/${DOMAIN}/privkey.pem" certs/
else
  echo "[1/2] 没有可用域名（或你要求自签），生成自签证书…"
  # 自签证书：浏览器会提示"不安全"，但流量仍然是加密的
  docker run --rm -v "$(pwd)/certs:/certs" alpine:3.20 \
    sh -c "apk add --no-cache openssl >/dev/null && \
           openssl req -x509 -nodes -newkey rsa:2048 -days 825 \
             -keyout /certs/privkey.pem -out /certs/fullchain.pem \
             -subj '/CN=soulpet'"
fi

if [ -f certs/fullchain.pem ] && [ -f certs/privkey.pem ]; then
  echo "[2/2] 证书就绪：deploy/certs/fullchain.pem"
  [ -n "$DOMAIN" ] && echo "      续期提醒：Let's Encrypt 证书 90 天到期，到期前重跑本脚本即可。"
  echo
  echo "接下来：docker compose up -d"
else
  echo "[x] 没生成出证书，请检查上面的报错。"
  exit 1
fi
