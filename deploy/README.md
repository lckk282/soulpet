# 云服务器部署

把 SoulPet 放到一台有公网 IP 的 Linux 服务器上，让它 7×24 在线。

**前置条件**：服务器上装了 Docker 与 Docker Compose（`docker --version` 有输出即可）。

---

## 一、三条命令跑起来

```bash
cd deploy

# 1) 配置
cp .env.example .env
vim .env                       # 至少改 SOULPET_MASTER_KEY 和 SOULPET_ACCESS_TOKEN

# 2) 准备 HTTPS 证书（一次性）
chmod +x init-certs.sh
./init-certs.sh                # 有域名 → Let's Encrypt；没域名 → ./init-certs.sh --self

# 3) 起服务
docker compose up -d
```

起来之后访问 `https://你的域名/?token=你在.env里设的口令`。

---

## 二、.env 每个字段什么意思

| 变量 | 必填 | 说明 |
|---|---|---|
| `SOULPET_MASTER_KEY` | **是** | 密钥加密主密码。**换了它已存的 API Key 就解不开了**，请记进密码管理器 |
| `SOULPET_ACCESS_TOKEN` | **公网必填** | 网页访问口令。不设的话，任何知道 IP 的人都能翻你的记忆 |
| `SOULPET_SECRET_LLM_API_KEY` | 否 | 直接用环境变量注入模型 Key，优先级高于界面里保存的 |
| `DOMAIN` | 有域名时填 | 如 `pet.example.com`。填了才会去签 Let's Encrypt |
| `EMAIL` | 有域名时填 | Let's Encrypt 的到期提醒邮箱 |

生成一个足够随机的口令：

```bash
openssl rand -base64 24
```

---

## 三、访问口令怎么工作

服务在公网打开后，**所有 `/api/*` 都会被拦住**，必须带口令。

**浏览器**：首次访问

```
https://你的域名/?token=你的口令
```

会自动写 Cookie 并把地址栏里的口令抹掉，之后 30 天免密。

**脚本 / 第三方调用**：

```
Authorization: Bearer 你的口令
```

**忘记口令了**：本地执行 `cat data/access_token.txt` 看（如果没设环境变量，程序会自动生成一个写在这里，同时打在 `data/logs/backend.log` 里）。

---

## 四、证书

### 有域名

1. 先把域名的 **A 记录**指到这台服务器。
2. 确认云厂商安全组放行了 **80 和 443**。
3. `./init-certs.sh` —— 它用 certbot standalone 临时占用 80 端口做校验。
   > 所以这个脚本必须在 `docker compose up` **之前**跑，否则 80 被 nginx 占了。

### 没域名

```bash
./init-certs.sh --self
```

生成自签证书。浏览器会红着提示"不安全"，点"继续前往"即可。流量依然是加密的，但别在公共 WiFi 环境下这么用。

### 续期

Let's Encrypt 证书 90 天到期。到期前重跑一次 `./init-certs.sh`（先删掉 `certs/fullchain.pem` 与 `certs/privkey.pem`）。

---

## 五、数据在哪

`docker-compose.yml` 把两个目录挂成了数据卷，删容器不丢数据：

```
deploy/config  →  /app/config    配置
deploy/data    →  /app/data      数据库、记忆、日志、备份、密钥
```

备份：

```bash
# 从宿主机直接拷，或进容器调接口
curl -X POST -H "Authorization: Bearer 你的口令" https://你的域名/api/status/backup
```

---

## 六、升级

```bash
cd deploy
docker compose down
git -C .. pull
docker compose build --no-cache
docker compose up -d
```

配置和数据都在卷里，升级不会动它们。

> `frontend/dist` 是随仓库发布的预构建产物，不需要在服务器上装 Node。

---

## 七、必须注意的安全事项

1. **不要改 `docker-compose.yml` 里 `127.0.0.1:8787:8787` 这行**。改成就 `8787:8787` 就是把裸 HTTP 接口直接挂到公网，绕过 nginx 和口令层的部分防护。
2. **接了 QQ 的话，NapCat 的 WebSocket 端口绝不能映射到公网**。要写 `127.0.0.1:3001:3001`。
3. `SOULPET_ACCESS_TOKEN` 不要用 `123456` 这类口令。这是你记忆库的唯一一道门。
4. 容器只监听回环，对外全靠 nginx。所以 nginx 挂了 = 服务不可访问，这是设计如此。

---

## 八、排错

```bash
# 看服务日志
docker compose logs -f soulpet

# 看 nginx 日志
docker compose logs -f nginx

# 容器健康状态
docker compose ps
```

| 现象 | 排查方向 |
|---|---|
| 502 Bad Gateway | soulpet 容器没起来。`docker compose logs soulpet` |
| 一直跳 https 打不开 | 证书没生成好。检查 `deploy/certs/` 里有没有两个 pem 文件 |
| 页面能开，但一直提示需要口令 | 地址里少了 `?token=`，或者口令和 .env 不一致 |
| 打字机效果变成一次性蹦出 | nginx 的 `proxy_buffering` 被改过了，确认它是 `off` |
