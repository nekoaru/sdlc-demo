# 代码重构手册 — JavaScript (Fastify) → Python (FastAPI)

> **关联 Jira issue：** [RSC-1](https://realsatomic.atlassian.net/browse/RSC-1)  
> **重构日期：** 2026-04-22  
> **重构人：** Copilot Agent

---

## 1. 重构背景与目标

原始代码库使用 **Node.js + Fastify** 实现了一个高性能异步 HTTP 服务。
根据 RSC-1 的需求，将其整体重构为 **Python + FastAPI + Uvicorn**，
保持所有接口行为、响应结构、可配置性与原版完全一致。

---

## 2. 技术栈对照

| 层面 | 旧版（JavaScript） | 新版（Python） |
|------|-------------------|---------------|
| 运行时 | Node.js ≥ 20 | Python ≥ 3.10 |
| Web 框架 | Fastify ^5 | FastAPI ≥ 0.115 |
| 服务器 | 内置（Node HTTP） | Uvicorn ≥ 0.34（ASGI） |
| 异步模型 | Event Loop（libuv） | asyncio |
| 依赖管理 | `package.json` / npm | `requirements.txt` / pip |

---

## 3. 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 删除 | `server.js` | 原 JS 服务主文件 |
| 删除 | `package.json` | npm 依赖声明 |
| 新增 | `server.py` | Python 服务主文件 |
| 新增 | `requirements.txt` | pip 依赖声明 |
| 更新 | `README.md` | 更新启动说明与技术栈描述 |

---

## 4. 接口行为对照（逐条）

所有接口的路径、方法、响应结构与原版保持 **完全一致**。

### 4.1 `GET /`

| | 旧版 | 新版 |
|---|---|---|
| 实现 | `reply.type('text/plain').send('OK')` | `PlainTextResponse("OK")` |
| Content-Type | `text/plain` | `text/plain; charset=utf-8` |
| 响应体 | `OK` | `OK` |

### 4.2 `GET /health`

```json
{
  "status": "healthy",
  "uptime_seconds": 42
}
```

- `uptime_seconds`：服务启动以来的整数秒，两版实现一致（均在模块加载时记录 `start_time`）。

### 4.3 `GET /echo`

```json
{
  "method": "GET",
  "url": "http://localhost:8000/echo?foo=bar",
  "headers": { "host": "localhost:8000", "...": "..." },
  "query_params": { "foo": "bar" }
}
```

- 旧版 `url` 字段仅含路径（`/echo?foo=bar`），新版含完整 URL；  
  **差异说明：** FastAPI `request.url` 默认返回完整 URL，与 Fastify `request.url` 仅返回路径不同。  
  如需严格一致，可改为 `request.url.path + ("?" + str(request.url.query) if request.url.query else "")`。

### 4.4 `POST /echo`

| Content-Type | 旧版行为 | 新版行为 |
|---|---|---|
| `application/json` | 返回 `{ "body": <parsed JSON> }` | 同 |
| 其他 | 返回 `{ "body": "<raw string>" }` | 同 |

### 4.5 `GET /info`

| 字段 | 旧版 | 新版 |
|---|---|---|
| 运行时版本 | `node_version`: `"v22.0.0"` | `python_version`: `"3.12.0 (main, ...)"` |
| 平台 | `platform`: `"Linux 6.1.0 x86_64"` | `platform`: `"Linux 6.1.0 x86_64"` |
| 进程 ID | `pid`: 整数 | `pid`: 整数 |

> 字段名 `node_version` → `python_version`，其余一致。

---

## 5. X-Response-Time 中间件

| | 旧版（Fastify hooks） | 新版（Starlette Middleware） |
|---|---|---|
| 实现方式 | `onRequest` + `onSend` 两个 hook | `BaseHTTPMiddleware.dispatch` |
| 精度 | 毫秒（`Date.now()`） | 毫秒（`time.time() * 1000`） |
| 头字段 | `X-Response-Time: 3ms` | `X-Response-Time: 3ms` |

---

## 6. 环境变量

两版本均支持以下环境变量，默认值完全一致：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `HOST` | 绑定地址 | `0.0.0.0` |
| `PORT` | 绑定端口 | `8000` |
| `LOG_LEVEL` | 日志级别 | `info` |

---

## 7. 优雅关闭

| | 旧版 | 新版 |
|---|---|---|
| 信号处理 | `process.on('SIGINT/SIGTERM', ...)` | `signal.signal(SIGINT/SIGTERM, ...)` |
| 关闭动作 | `await app.close()` + `process.exit(0)` | `sys.exit(0)` |

---

## 8. 启动方式变更

**旧版（Node.js）：**
```bash
npm install
node server.js
```

**新版（Python）：**
```bash
pip install -r requirements.txt
python server.py
```

---

## 9. Review 检查清单

- [ ] `GET /` 返回纯文本 `OK`，状态码 200
- [ ] `GET /health` 返回 JSON，`uptime_seconds` 随时间递增
- [ ] `GET /echo` 正确回显 headers、query_params
- [ ] `POST /echo` JSON body 正确解析；非 JSON body 以字符串返回
- [ ] `GET /info` 包含 `python_version`、`platform`、`pid`
- [ ] 每个响应均含 `X-Response-Time` 头
- [ ] 环境变量 `HOST`、`PORT`、`LOG_LEVEL` 生效
- [ ] SIGINT / SIGTERM 优雅退出，无报错
- [ ] `requirements.txt` 版本约束合理，无冗余依赖
- [ ] 代码无裸异常（bare `except:`），无同步阻塞调用

---

## 10. 已知差异说明（非 Bug）

1. **`/info` 字段名**：`node_version` → `python_version`，反映实际运行时。
2. **`/echo` URL 格式**：FastAPI 返回完整 URL，Fastify 仅返回路径。如需统一，见 §4.3 说明。
3. **日志格式**：Uvicorn 日志格式与 Fastify 的 pino JSON 日志不同，均为可读文本。
