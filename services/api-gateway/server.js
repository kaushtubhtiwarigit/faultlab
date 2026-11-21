require('./tracing');
const express = require('express');
const { createClient } = require('redis');
const { trace } = require('@opentelemetry/api');

const app = express();
app.use(express.json());

const tracer = trace.getTracer('api-gateway');

let redisClient;

async function initRedis() {
  redisClient = createClient({
    socket: {
      host: process.env.REDIS_HOST || 'redis',
      port: process.env.REDIS_PORT || 6379
    }
  });

  redisClient.on('error', (err) => console.error('Redis Client Error', err));
  await redisClient.connect();
  console.log('Connected to Redis');
}

app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'api-gateway' });
});

app.post('/orders', async (req, res) => {
  const span = tracer.startSpan('create-order');
  
  try {
    const { customer_id, amount } = req.body;
    
    if (!customer_id || !amount) {
      span.setStatus({ code: 1, message: 'Invalid request' });
      span.end();
      return res.status(400).json({ error: 'customer_id and amount required' });
    }

    const order_id = `ORD-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    const orderData = JSON.stringify({
      order_id,
      customer_id,
      amount: parseFloat(amount),
      timestamp: new Date().toISOString()
    });

    span.setAttribute('order.id', order_id);
    span.setAttribute('order.amount', amount);
    
    // Push to Redis queue for async processing
    await redisClient.lPush('order_queue', orderData);
    
    span.setStatus({ code: 0 });
    span.end();
    
    res.status(202).json({
      message: 'Order accepted',
      order_id,
      status: 'queued'
    });
    
  } catch (error) {
    span.setStatus({ code: 2, message: error.message });
    span.end();
    console.error('Error creating order:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

app.get('/orders/stats', async (req, res) => {
  const span = tracer.startSpan('get-order-stats');
  
  try {
    const queueLength = await redisClient.lLen('order_queue');
    
    span.setAttribute('queue.length', queueLength);
    span.setStatus({ code: 0 });
    span.end();
    
    res.json({
      queue_length: queueLength,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    span.setStatus({ code: 2, message: error.message });
    span.end();
    res.status(500).json({ error: error.message });
  }
});

const PORT = process.env.API_PORT || 3000;

initRedis().then(() => {
  app.listen(PORT, () => {
    console.log(`API Gateway listening on port ${PORT}`);
  });
}).catch(err => {
  console.error('Failed to start server:', err);
  process.exit(1);
});
