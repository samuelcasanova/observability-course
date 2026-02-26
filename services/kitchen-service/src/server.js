// OTel instrumentation MUST be the first import
import "./tracing.js";

import express from "express";
import {
  collectDefaultMetrics,
  Counter,
  Histogram,
  register,
} from "prom-client";
import { logger } from "./logger.js";
import { trace, SpanStatusCode } from "@opentelemetry/api";
import { connectRabbitMQ, closeRabbitMQ, publishOrder } from "./rabbitmq.js";

const app = express();
app.use(express.json());

collectDefaultMetrics({ prefix: "kitchen_" });

const preparedCounter = new Counter({
  name: "kitchen_orders_prepared_total",
  help: "Total orders prepared",
  labelNames: ["status"],
});

const prepDuration = new Histogram({
  name: "kitchen_preparation_duration_seconds",
  help: "Time to prepare an order",
  buckets: [0.5, 1, 2, 3, 5, 8],
});

const FAILURE_RATE = 0.1; // 10% random failure to generate error spans

app.get("/health", (_req, res) => {
  res.json({ status: "ok", service: "kitchen-service" });
});

app.get("/metrics", async (_req, res) => {
  res.set("Content-Type", register.contentType);
  res.end(await register.metrics());
});

app.post("/prepare", async (req, res) => {
  const { order_id, restaurant, items } = req.body;
  const tracer = trace.getTracer("kitchen-service");

  const span = tracer.startSpan("kitchen.prepare");
  const start = Date.now();

  logger.info("Starting order preparation", {
    order_id,
    restaurant,
    items_count: items?.length,
  });

  // Simulate random failure (generates error spans in Jaeger)
  if (Math.random() < FAILURE_RATE) {
    const errMsg = "Kitchen equipment malfunction";
    span.recordException(new Error(errMsg));
    span.setStatus({ code: SpanStatusCode.ERROR, message: errMsg });
    span.end();
    preparedCounter.inc({ status: "failed" });
    logger.error("Order preparation failed", {
      order_id,
      restaurant,
      error: errMsg,
    });
    return res.status(500).json({ error: errMsg, order_id });
  }

  // Simulate food preparation delay (1–5 seconds)
  const delay = Math.floor(Math.random() * 4000) + 1000;
  await new Promise((resolve) => setTimeout(resolve, delay));

  const durationSec = (Date.now() - start) / 1000;
  prepDuration.observe(durationSec);
  preparedCounter.inc({ status: "success" });

  logger.info("Order prepared, publishing to queue", {
    order_id,
    prep_duration_s: durationSec.toFixed(2),
  });

  // ── Async hand-off: publish to RabbitMQ instead of HTTP call ────────────────
  // The publishOrder function creates a PRODUCER span and injects the current
  // trace context (traceparent header) into the AMQP message — so Delivery
  // Service can resume this trace when it consumes the message.
  try {
    await publishOrder({ order_id, restaurant, items });
    span.setStatus({ code: SpanStatusCode.OK });
    span.end();
    return res.json({ status: "prepared", order_id });
  } catch (err) {
    span.recordException(err);
    span.setStatus({ code: SpanStatusCode.ERROR, message: err.message });
    span.end();
    preparedCounter.inc({ status: "failed" });
    logger.error("Failed to publish order to queue", {
      order_id,
      error: err.message,
    });
    return res.status(500).json({ error: "Queue unavailable", order_id });
  }
});

const PORT = process.env.PORT || 3001;

// Connect to RabbitMQ before accepting requests
connectRabbitMQ()
  .then(() => {
    const server = app.listen(PORT, () => {
      logger.info(`Kitchen service listening on port ${PORT}`);
    });

    process.on("SIGTERM", async () => {
      logger.info("Shutting down kitchen service...");
      await closeRabbitMQ();
      server.close(() => process.exit(0));
    });
  })
  .catch((err) => {
    logger.error("Fatal: could not connect to RabbitMQ", {
      error: err.message,
    });
    process.exit(1);
  });
