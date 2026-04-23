/**
 * High-performance async HTTP server built with Express.js + Node.js.
 *
 * Features:
 *   - Async request handling via Node.js event loop
 *   - JSON / plain-text / health endpoints
 *   - Graceful shutdown (SIGINT / SIGTERM)
 *   - Configurable via environment variables
 *   - X-Response-Time header on every response
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

const express = require('express');
const os = require('os');
const process = require('process');

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const HOST = process.env.HOST || '0.0.0.0';
const PORT = parseInt(process.env.PORT || '8000', 10);
const LOG_LEVEL = (process.env.LOG_LEVEL || 'info').toLowerCase();

const startTime = Date.now();

// ---------------------------------------------------------------------------
// App setup
// ---------------------------------------------------------------------------

const app = express();
app.use(express.json());
app.use(express.text());

// ---------------------------------------------------------------------------
// Middleware – add X-Response-Time to every response
// ---------------------------------------------------------------------------

app.use((req, res, next) => {
  const ts = Date.now();
  res.on('finish', () => {
    const elapsedMs = Date.now() - ts;
    // Header already set means it was set before finish; skip override
  });
  // Set header before sending
  const originalSend = res.send.bind(res);
  const originalJson = res.json.bind(res);

  const setResponseTime = () => {
    if (!res.headersSent) {
      res.setHeader('X-Response-Time', `${Date.now() - ts}ms`);
    }
  };

  res.send = function (...args) {
    setResponseTime();
    return originalSend(...args);
  };

  res.json = function (...args) {
    setResponseTime();
    return originalJson(...args);
  };

  next();
});

// ---------------------------------------------------------------------------
// Routes
// ---------------------------------------------------------------------------

// GET / – health probe
app.get('/', (req, res) => {
  res.type('text/plain').send('OK');
});

// GET /health – JSON status + uptime
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    uptime_seconds: Math.round((Date.now() - startTime) / 1000),
  });
});

// GET /echo – echo request metadata
app.get('/echo', (req, res) => {
  res.json({
    method: req.method,
    url: `${req.protocol}://${req.get('host')}${req.originalUrl}`,
    headers: req.headers,
    query_params: req.query,
  });
});

// POST /echo – echo request body
app.post('/echo', async (req, res) => {
  const contentType = req.headers['content-type'] || '';
  let body;
  if (contentType.includes('application/json')) {
    body = req.body;
  } else {
    body = typeof req.body === 'string' ? req.body : JSON.stringify(req.body);
  }
  res.json({ body });
});

// GET /info – runtime info
app.get('/info', (req, res) => {
  res.json({
    node_version: process.version,
    platform: `${os.type()} ${os.release()} ${os.arch()}`,
    pid: process.pid,
  });
});

// ---------------------------------------------------------------------------
// Graceful shutdown
// ---------------------------------------------------------------------------

let server;

function shutdown(signal) {
  console.log(`\nReceived signal ${signal}. Shutting down…`);
  server.close(() => {
    console.log('Server closed.');
    process.exit(0);
  });
}

process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------

server = app.listen(PORT, HOST, () => {
  if (LOG_LEVEL !== 'silent') {
    console.log(`Server running at http://${HOST}:${PORT}`);
  }
});
