# 重构手册：Python (FastAPI) → JavaScript (Express.js)

> **关联 Jira Issue**: RSC-1 – 代码库重构  
> **重构日期**: 2026-04-23  
> **重构人**: Copilot Agent

---

## 1. 重构目标

将原 Python（FastAPI + Uvicorn）实现的 HTTP 服务完整迁移至 JavaScript（Express.js + Node.js），保持所有 API 端点的行为和响应格式不变。

---

## 2. 技术栈映射

| 层次 | 原（Python） | 新（JavaScript） |
|------|-------------|-----------------|
| 运行时 | CPython 3.x | Node.js ≥ 18 |
| Web 框架 | FastAPI | Express.js |
| 服务器 | Uvicorn (ASGI) | Node.js 内建 HTTP |
| 依赖管理 | pip + requirements.txt | npm + package.json |
| 异步模型 | asyncio / async-await | Event Loop / async-await |
| 平台信息 | `platform` / `sys` 模块 | `os` / `process` 模块 |

---

## 3. 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 删除 | `server.py` | Python 原始实现 |
| 删除 | `requirements.txt` | Python 依赖声明 |
| 新增 | `server.js` | JavaScript 重构实现 |
| 新增 | `package.json` | Node.js 依赖声明 |
| 修改 | `README.md` | 更新启动命令及技术栈描述 |
| 新增 | `REFACTORING.md` | 本手册 |

---

## 4. 逐段代码对照

### 4.1 应用初始化

**Python (FastAPI)**
```python
app = FastAPI(lifespan=lifespan)
app.add_middleware(ResponseTimeMiddleware)
```

**JavaScript (Express)**
```javascript
const app = express();
app.use(express.json());
app.use(express.text());
// X-Response-Time 中间件内联注册
app.use((req, res, next) => { ... });
```

> FastAPI 的 `lifespan` 用于管理启动/关闭生命周期；Express 无等价概念，通过 `server.close()` 实现优雅关闭。

---

### 4.2 X-Response-Time 中间件

**Python**
```python
class ResponseTimeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        ts = time.time()
        response = await call_next(request)
        elapsed_ms = int((time.time() - ts) * 1000)
        response.headers["X-Response-Time"] = f"{elapsed_ms}ms"
        return response
```

**JavaScript**
```javascript
app.use((req, res, next) => {
  const ts = Date.now();
  const originalSend = res.send.bind(res);
  res.send = function (...args) {
    res.setHeader('X-Response-Time', `${Date.now() - ts}ms`);
    return originalSend(...args);
  };
  next();
});
```

> Python 版本在 `call_next` 返回后设置响应头；JavaScript 中通过包装 `res.send` 在实际发送前注入头部。

---

### 4.3 路由端点

#### GET /
| | Python | JavaScript |
|---|---|---|
| 装饰器/方法 | `@app.get("/", response_class=PlainTextResponse)` | `app.get('/', ...)` |
| 返回值 | `return "OK"` | `res.type('text/plain').send('OK')` |

#### GET /health
```python
# Python
{"status": "healthy", "uptime_seconds": round(time.time() - start_time)}
```
```javascript
// JavaScript
{"status": "healthy", "uptime_seconds": Math.round((Date.now() - startTime) / 1000)}
```
> `time.time()` 返回秒级浮点，`Date.now()` 返回毫秒整数，需除以 1000 对齐。

#### GET /echo
```python
# Python – 使用 request 对象
{"method": request.method, "url": str(request.url),
 "headers": dict(request.headers), "query_params": dict(request.query_params)}
```
```javascript
// JavaScript – 使用 req 对象
{"method": req.method, "url": `${req.protocol}://${req.get('host')}${req.originalUrl}`,
 "headers": req.headers, "query_params": req.query}
```

#### POST /echo
```python
# Python – 手动解析 content-type
if "application/json" in content_type:
    body = await request.json()
else:
    raw = await request.body()
    body = raw.decode("utf-8", errors="replace")
```
```javascript
// JavaScript – express.json() / express.text() 中间件已自动解析
const body = contentType.includes('application/json') ? req.body : req.body;
```
> Express 的 `express.json()` 和 `express.text()` 中间件已在全局挂载，`req.body` 自动为解析后的值。

#### GET /info
```python
# Python
{"python_version": sys.version, "platform": f"{platform.system()} {platform.release()} {platform.machine()}", "pid": os.getpid()}
```
```javascript
// JavaScript
{"node_version": process.version, "platform": `${os.type()} ${os.release()} ${os.arch()}`, "pid": process.pid}
```
> 字段名由 `python_version` 改为 `node_version`，其余格式保持一致。

---

### 4.4 优雅关闭

**Python**
```python
def handle_signal(sig, frame):
    sys.exit(0)

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)
```

**JavaScript**
```javascript
process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));

function shutdown(signal) {
  server.close(() => process.exit(0));
}
```

> JavaScript 版本通过 `server.close()` 等待现有连接处理完毕后再退出，比 Python 的 `sys.exit(0)` 更优雅。

---

### 4.5 服务器启动

**Python**
```python
uvicorn.run(app, host=HOST, port=PORT, log_level=LOG_LEVEL)
```

**JavaScript**
```javascript
server = app.listen(PORT, HOST, () => {
  console.log(`Server running at http://${HOST}:${PORT}`);
});
```

---

## 5. 行为差异说明

| 项目 | Python 原版 | JavaScript 新版 | 影响 |
|------|------------|----------------|------|
| `/info` 字段名 | `python_version` | `node_version` | 接口字段名变更 |
| 时间精度 | `time.time()` 秒级 | `Date.now()` 毫秒级 | 内部实现差异，对外表现一致 |
| 请求体解析 | 手动读取 raw body | Express 中间件自动解析 | 行为等价 |
| 关闭方式 | `sys.exit(0)` 立即退出 | `server.close()` 等待连接 | 新版更优雅 |

---

## 6. 本地验证步骤

```bash
# 安装依赖
npm install

# 启动服务
npm start

# 验证端点
curl http://localhost:8000/
curl http://localhost:8000/health
curl http://localhost:8000/echo?foo=bar
curl -X POST http://localhost:8000/echo -H "Content-Type: application/json" -d '{"key":"value"}'
curl http://localhost:8000/info
```

---

## 7. Review 核查清单

- [ ] `GET /` 返回纯文本 `OK`，状态码 200
- [ ] `GET /health` 返回 `{"status":"healthy","uptime_seconds":N}`
- [ ] `GET /echo` 回显 method / url / headers / query_params
- [ ] `POST /echo` (JSON) 正确回显 JSON body
- [ ] `POST /echo` (text/plain) 正确回显文本 body
- [ ] `GET /info` 返回 node_version / platform / pid
- [ ] 所有响应包含 `X-Response-Time` 头
- [ ] SIGINT / SIGTERM 触发优雅关闭
- [ ] 环境变量 HOST / PORT / LOG_LEVEL 生效
