# sdlc-demo

高性能异步 HTTP 服务示例，使用 **Fastify**（Node.js 最高性能 Web 框架）。

> 关联 Jira issue：[RSC-1](https://realsatomic.atlassian.net/browse/RSC-1) — 把代码语言从Python改为JavaScript

## 快速开始

```bash
npm install
node server.js
```

默认监听 `0.0.0.0:8000`，可通过环境变量覆盖：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `HOST` | 绑定地址 | `0.0.0.0` |
| `PORT` | 绑定端口 | `8000` |
| `LOG_LEVEL` | 日志级别 | `info` |

## API 端点

| Method | Path | 说明 |
|--------|------|------|
| GET | `/` | 健康探针，返回 `OK` |
| GET | `/health` | JSON 状态 + 服务运行时长 |
| GET | `/echo` | 回显请求头、URL、查询参数 |
| POST | `/echo` | 回显请求体（JSON 或纯文本） |
| GET | `/info` | Node.js 版本、平台、进程 PID |

每个响应均附带 `X-Response-Time` 头，记录本次请求处理耗时（毫秒）。

## 文件结构

```
server.js     # 全部逻辑，单文件
package.json  # 依赖声明
README.md
```
