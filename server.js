/**
 * High-performance async HTTP server built with Fastify.
 *
 * Features:
 *   - Fully async request handling via Node.js event loop
 *   - JSON / plain-text / health endpoints
 *   - Graceful shutdown (SIGINT / SIGTERM)
 *   - Configurable via environment variables
 *
 * Usage:
 *   npm install
 *   node server.js
 *
 * Environment variables:
 *   HOST      - bind address  (default: 0.0.0.0)
 *   PORT      - bind port     (default: 8000)
 *   LOG_LEVEL - log level     (default: info)
 */

'use strict';

const os = require('node:os');
const process = require('node:process');

const Fastify = require('fastify');

// ---------------------------------------------------------------------------
// App setup
// ---------------------------------------------------------------------------

const host = process.env.HOST ?? '0.0.0.0';
const port = Number(process.env.PORT ?? 8000);
const logLevel = process.env.LOG_LEVEL ?? 'info';

const app = Fastify({
  logger: { level: logLevel },
  // Performance options
  trustProxy: true,
});

const startTime = Date.now();

// ---------------------------------------------------------------------------
// Middleware – add X-Response-Time to every response
// ---------------------------------------------------------------------------

app.addHook('onSend', async (request, reply) => {
  const elapsed = Date.now() - (request.startTs ?? Date.now());
  reply.header('X-Response-Time', `${elapsed}ms`);
});

app.addHook('onRequest', async (request) => {
  request.startTs = Date.now();
});

// ---------------------------------------------------------------------------
// Routes
// ---------------------------------------------------------------------------

app.get('/', async (_request, reply) => {
  reply.type('text/plain').send('OK');
});

app.get('/health', async () => {
  return {
    status: 'healthy',
    uptime_seconds: Math.round((Date.now() - startTime) / 1000),
  };
});

app.get('/echo', async (request) => {
  return {
    method: request.method,
    url: request.url,
    headers: request.headers,
    query_params: request.query,
  };
});

app.post('/echo', async (request, reply) => {
  const contentType = request.headers['content-type'] ?? '';
  if (contentType.includes('application/json')) {
    return { body: request.body };
  }
  // raw body (Fastify parses JSON automatically; non-JSON comes as Buffer/string)
  const raw = request.body;
  return { body: typeof raw === 'string' ? raw : String(raw ?? '') };
});

app.get('/info', async () => {
  return {
    node_version: process.version,
    platform: `${os.type()} ${os.release()} ${os.arch()}`,
    pid: process.pid,
  };
});

// ---------------------------------------------------------------------------
// Graceful shutdown
// ---------------------------------------------------------------------------

async function shutdown(signal) {
  app.log.info(`Received ${signal}. Shutting down…`);
  await app.close();
  process.exit(0);
}

process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------

(async () => {
  try {
    await app.listen({ host, port });
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
})();
