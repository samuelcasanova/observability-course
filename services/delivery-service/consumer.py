"""
RabbitMQ consumer for the Delivery Service.

Key observability concept: trace context is *extracted* from the AMQP message
headers and used to start a CONSUMER span that is a continuation of the trace
started by the Kitchen Service PRODUCER span.

In Jaeger this appears as a linked span — the trace crosses the async
boundary and you can follow the full journey from order creation to delivery.
"""

import asyncio
import json
import logging
import os

import aio_pika
from opentelemetry import trace
from opentelemetry.propagate import extract
from opentelemetry.trace import SpanKind

logger = logging.getLogger("delivery-service.consumer")

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
QUEUE_NAME = os.getenv("RABBITMQ_QUEUE", "orders.ready")


async def start_consumer(process_delivery_fn, tracer: trace.Tracer):
    """
    Connect to RabbitMQ and start consuming from the orders queue.
    `process_delivery_fn` is injected to avoid circular imports with main.py.
    """
    retries = 15
    delay = 3

    connection = None
    for attempt in range(1, retries + 1):
        try:
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            break
        except Exception as exc:
            logger.warning(
                "RabbitMQ not ready, retrying...",
                extra={"attempt": attempt, "max": retries, "error": str(exc)},
            )
            await asyncio.sleep(delay)

    if connection is None:
        raise RuntimeError("Could not connect to RabbitMQ after retries")

    channel = await connection.channel()
    await channel.set_qos(prefetch_count=5)

    queue = await channel.declare_queue(QUEUE_NAME, durable=True)
    logger.info("Consumer ready, waiting for messages", extra={"queue": QUEUE_NAME})

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                await _handle_message(message, process_delivery_fn, tracer)


async def _handle_message(message: aio_pika.IncomingMessage, process_delivery_fn, tracer):
    """
    Process a single message from the queue.

    The critical step is extracting the W3C traceparent/tracestate from the
    message headers, then starting a CONSUMER span *within that context*.
    This links the Delivery span to the Kitchen PRODUCER span in Jaeger.
    """
    try:
        # ── Extract trace context from AMQP message headers ──────────────────
        # aio-pika returns header values as strings for string-typed AMQP fields.
        # We normalise to str just in case.
        raw_headers = message.headers or {}
        carrier = {
            k: v.decode() if isinstance(v, bytes) else str(v)
            for k, v in raw_headers.items()
        }

        # extract() returns the remote context encoded in traceparent/tracestate
        ctx = extract(carrier)

        data = json.loads(message.body)
        order_id = data.get("order_id", "unknown")
        restaurant = data.get("restaurant", "Unknown")

        logger.info(
            "Message received from queue",
            extra={"order_id": order_id, "queue": QUEUE_NAME, "carrier": carrier},
        )

        # Start CONSUMER span linked to the Kitchen PRODUCER span
        with tracer.start_as_current_span(
            f"{QUEUE_NAME} receive",
            context=ctx,
            kind=SpanKind.CONSUMER,
        ) as span:
            span.set_attributes({
                "messaging.system": "rabbitmq",
                "messaging.destination": QUEUE_NAME,
                "messaging.destination_kind": "queue",
                "messaging.operation": "receive",
                "order.id": order_id,
            })

            await process_delivery_fn(order_id, restaurant)

    except Exception as exc:
        logger.error(
            "Failed to process message",
            extra={"error": str(exc)},
            exc_info=True,
        )
        raise
