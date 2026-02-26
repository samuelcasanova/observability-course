/**
 * RabbitMQ publisher for the Kitchen Service.
 *
 * Key observability concept: trace context is injected into the AMQP message
 * headers using the W3C propagation format (traceparent / tracestate).
 * The Delivery Service consumer extracts this context and creates a CONSUMER
 * span that links back to this PRODUCER span — forming a cross-process trace.
 */
import amqplib from "amqplib";
import {
  propagation,
  context,
  trace,
  SpanKind,
  SpanStatusCode,
} from "@opentelemetry/api";
import { logger } from "./logger.js";

const RABBITMQ_URL =
  process.env.RABBITMQ_URL || "amqp://guest:guest@localhost:5672";
const QUEUE_NAME = process.env.RABBITMQ_QUEUE || "orders.ready";

let connection = null;
let channel = null;

export async function connectRabbitMQ(retries = 10, delayMs = 3000) {
  for (let i = 1; i <= retries; i++) {
    try {
      connection = await amqplib.connect(RABBITMQ_URL);
      channel = await connection.createChannel();
      // durable: true — queue survives broker restarts
      await channel.assertQueue(QUEUE_NAME, { durable: true });
      logger.info("Connected to RabbitMQ", { queue: QUEUE_NAME });
      return;
    } catch (err) {
      logger.warn(`RabbitMQ not ready, retrying (${i}/${retries})...`, {
        error: err.message,
      });
      await new Promise((r) => setTimeout(r, delayMs));
    }
  }
  throw new Error("Could not connect to RabbitMQ after retries");
}

/**
 * Publish an order to the queue.
 * Creates a PRODUCER span and injects traceparent/tracestate into message headers.
 */
export async function publishOrder(orderData) {
  const tracer = trace.getTracer("kitchen-service");

  return tracer.startActiveSpan(
    "orders.ready publish",
    { kind: SpanKind.PRODUCER },
    async (span) => {
      span.setAttributes({
        "messaging.system": "rabbitmq",
        "messaging.destination": QUEUE_NAME,
        "messaging.destination_kind": "queue",
        "order.id": orderData.order_id,
      });

      // ── Inject trace context into AMQP message headers ──────────────────────
      // This is the critical step: without this, the Delivery consumer would
      // start an unrelated trace with no link to this Kitchen trace.
      const carrier = {};
      propagation.inject(context.active(), carrier);
      // carrier is now: { traceparent: '00-<traceId>-<spanId>-01', tracestate: '' }

      const payload = Buffer.from(JSON.stringify(orderData));
      channel.sendToQueue(QUEUE_NAME, payload, {
        persistent: true, // survives broker restart
        contentType: "application/json",
        headers: carrier, // W3C traceparent lives here
      });

      span.setStatus({ code: SpanStatusCode.OK });
      span.end();

      logger.info("Order published to queue", {
        order_id: orderData.order_id,
        queue: QUEUE_NAME,
        trace_context: carrier,
      });
    },
  );
}

export async function closeRabbitMQ() {
  await channel?.close();
  await connection?.close();
}
