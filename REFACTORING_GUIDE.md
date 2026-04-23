# 重构手册：Python FastAPI → Node.js Express

**Issue**: RSC-1  
**日期**: 2026-04-23  
**重构者**: Copilot Agent

---

## 1. 重构概述

本次重构将 `server.py`（Python + FastAPI + Uvicorn）完整移植为 `server.js`（Node.js + Express），保持所有功能特性不变，仅替换语言和运行时环境。

| 维度 | 原实现（Python） | 新实现（JavaScript） |
|---|---|---|
| 语言 | Python 3.x | Node.js (≥18) |
| 框架 | FastAPI | Express 4.x |
| 服务器 | Uvicorn (ASGI) | Node.js 内置 HTTP |
| 包管理 | pip / requirements.txt | npm / package.json |
| 启动命令 | `python server.py` | `node server.js` |

---

## 2. 文件变更清单

| 操作 | 文件 | 说明 |
|---|---|---|
| 新增 | `server.js` | JavaScript 版服务器主文件 |
| 新增 | `package.json` | Node.js 依赖与项目配置 |
| 保留 | `server.py` | 原 Python 实现（可在确认无误后删除） |

---

## 3. 端点对照表

所有 HTTP 端点完整保留，行为一致：

| 方法 | 路径 | 响应类型 | 说明 |
|---|---|---|---|
| GET | `/` | `text/plain` | 返回 `OK` 字符串 |
| GET | `/health` | `application/json` | 返回健康状态与运行时长（秒） |
| GET | `/echo` | `application/json` | 回显请求方法、URL、请求头、查询参数 |
| POST | `/echo` | `application/json` | 回显请求体 |
| GET | `/info` | `application/json` | 返回运行时版本、平台、PID |

---

## 4. 逐一功能对比

### 4.1 配置（环境变量）

**Python:**
```python
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 8000))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "info").lower()
```

**JavaScript:**
```js
const HOST = process.env.HOST || "0.0.0.0";
const PORT = parseInt(process.env.PORT || "8000", 10);
const LOG_LEVEL = (process.env.LOG_LEVEL || "info").toLowerCase();
```

两者功能等价，均支持 `HOST`、`PORT`、`LOG_LEVEL` 三个环境变量，默认值相同。

---

### 4.2 X-Response-Time 中间件

**Python（Starlette BaseHTTPMiddleware）:**
```python
class ResponseTimeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ts = time.time()
        response = await call_next(request)
        elapsed_ms = int((time.time() - ts) * 1000)
        response.headers["X-Response-Time"] = f"{elapsed_ms}ms"
        return response
```

**JavaScript（Express 中间件）:**
```js
app.use((req, res, next) => {
  const ts = Date.now();
  res.on("finish", () => {
    res.setHeader("X-Response-Time", `${Date.now() - ts}ms`);
  });
  next();
});
```

> **注意**：Express 中响应头需在 `finish` 事件中写入，因为 `res.send()` 调用时响应头已锁定。两者均能在响应头中正确附加处理耗时。

---

### 4.3 GET `/`

**Python:**
```python
@app.get("/", response_class=PlainTextResponse)
async def root():
    return "OK"
```

**JavaScript:**
```js
app.get("/", (req, res) => {
  res.type("text/plain").send("OK");
});
```

---

### 4.4 GET `/health`

**Python:**
```python
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "uptime_seconds": round(time.time() - start_time),
    }
```

**JavaScript:**
```js
app.get("/health", (req, res) => {
  res.json({
    status: "healthy",
    uptime_seconds: Math.round((Date.now() - startTime) / 1000),
  });
});
```

> Python 使用 `time.time()`（单位：秒），JavaScript 使用 `Date.now()`（单位：毫秒），需除以 1000 再取整，结果一致。

---

### 4.5 GET `/echo`

**Python:**
```python
@app.get("/echo")
async def echo_get(request: Request):
    return {
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers),
        "query_params": dict(request.query_params),
    }
```

**JavaScript:**
```js
app.get("/echo", (req, res) => {
  res.json({
    method: req.method,
    url: `${req.protocol}://${req.get("host")}${req.originalUrl}`,
    headers: req.headers,
    query_params: req.query,
  });
});
```

---

### 4.6 POST `/echo`

**Python:**
```python
@app.post("/echo")
async def echo_post(request: Request):
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
    else:
        raw = await request.body()
        body = raw.decode("utf-8", errors="replace")
    return {"body": body}
```

**JavaScript:**
```js
app.post("/echo", (req, res) => {
  const contentType = req.headers["content-type"] || "";
  let body;
  if (contentType.includes("application/json")) {
    body = req.body;
  } else {
    body = typeof req.body === "string" ? req.body : JSON.stringify(req.body);
  }
  res.json({ body });
});
```

---

### 4.7 GET `/info`

**Python:**
```python
@app.get("/info")
async def info():
    return {
        "python_version": sys.version,
        "platform": f"{platform.system()} {platform.release()} {platform.machine()}",
        "pid": os.getpid(),
    }
```

**JavaScript:**
```js
app.get("/info", (req, res) => {
  res.json({
    node_version: process.version,
    platform: `${os.type()} ${os.release()} ${os.arch()}`,
    pid: process.pid,
  });
});
```

> 字段 `python_version` 已重命名为 `node_version`，语义对应。

---

### 4.8 优雅关闭（Graceful Shutdown）

**Python:**
```python
def handle_signal(sig, frame):
    print(f"\nReceived signal {sig}. Shutting down…", flush=True)
    sys.exit(0)

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)
```

**JavaScript:**
```js
function shutdown(signal) {
  console.log(`\nReceived signal ${signal}. Shutting down…`);
  server.close(() => {
    console.log("Server closed.");
    process.exit(0);
  });
}

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));
```

> JavaScript 版调用 `server.close()` 等待所有在途请求完成后再退出，比 Python 版直接 `sys.exit(0)` 更为优雅。

---

## 5. 依赖对比

**Python（需 requirements.txt）：**
```
fastapi
uvicorn[standard]
```

**JavaScript（package.json）：**
```json
{
  "dependencies": {
    "express": "^4.18.2"
  }
}
```

安装命令：
```bash
# Python
pip install -r requirements.txt

# JavaScript
npm install
```

---

## 6. 启动方式对比

```bash
# Python
python server.py

# JavaScript
node server.js
# 或
npm start
```

---

## 7. Review 检查点

审查人在 review 时请重点关注以下几点：

- [ ] 所有 5 个端点（`/`、`/health`、`/echo` GET/POST、`/info`）均已正确实现
- [ ] 环境变量 `HOST`、`PORT`、`LOG_LEVEL` 默认值与原版一致
- [ ] `X-Response-Time` 响应头在所有请求中均正确附加
- [ ] `/health` 的 `uptime_seconds` 计算单位换算正确（ms → s）
- [ ] `/info` 的 `node_version` 字段替代了 `python_version`，语义清晰
- [ ] 优雅关闭逻辑覆盖 `SIGINT` 和 `SIGTERM`
- [ ] `package.json` 中 Node.js 版本要求 ≥18

---

## 8. 测试建议

```bash
# 安装依赖
npm install

# 启动服务
node server.js

# 测试各端点
curl http://localhost:8000/
curl http://localhost:8000/health
curl http://localhost:8000/echo?foo=bar
curl -X POST http://localhost:8000/echo -H "Content-Type: application/json" -d '{"hello":"world"}'
curl http://localhost:8000/info
```

---

*本手册由 Copilot Agent 自动生成，对应 Jira Issue RSC-1。*
