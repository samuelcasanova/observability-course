import asyncio
import logging
import os
import random
import time
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_fastapi_instrumentator import Instrumentator
from pythonjsonlogger import jsonlogger

from consumer import start_consumer

# ─── Logging ──────────────────────────────────────────────────────────────────
logger = logging.getLogger("delivery-service")
handler = logging.StreamHandler()
handler.setFormatter(
    jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"},
    )
)
logger.addHandler(handler)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

# ─── OpenTelemetry Setup ───────────────────────────────────────────────────────
OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "delivery-service")
resource = Resource.create({"service.name": SERVICE_NAME})

tracer_provider = TracerProvider(resource=resource)
tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True)))
trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer(SERVICE_NAME)

metric_reader = PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=OTLP_ENDPOINT, insecure=True))
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(SERVICE_NAME)

delivery_duration = meter.create_histogram(
    name="delivery_duration_seconds",
    description="Simulated delivery duration in seconds",
    unit="s",
)
deliveries_counter = meter.create_counter(
    name="deliveries_total",
    description="Total deliveries assigned",
)

HTTPXClientInstrumentor().instrument()

# ─── In-Memory Store ───────────────────────────────────────────────────────────
deliveries: dict[str, dict] = {}

NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:3002")
DRIVERS = ["Alice", "Bob", "Carlos", "Diana", "Eve"]


def fake_gps():
    """Generate a random GPS coordinate near Paris."""
    return {
        "lat": round(48.8566 + random.uniform(-0.05, 0.05), 6),
        "lng": round(2.3522 + random.uniform(-0.05, 0.05), 6),
    }


# ─── Core Business Logic ───────────────────────────────────────────────────────
# This function is called from BOTH the RabbitMQ consumer and (optionally) the
# HTTP endpoint below, keeping the logic DRY.
async def process_delivery(order_id: str, restaurant: str) -> dict:
    """Assign a driver and notify the customer. Called from the AMQP consumer."""
    driver = random.choice(DRIVERS)
    delivery_id = str(uuid.uuid4())[:8]

    with tracer.start_as_current_span("delivery.assign") as span:
        span.set_attribute("delivery.id", delivery_id)
        span.set_attribute("delivery.driver", driver)
        span.set_attribute("order.id", order_id)
        span.set_attribute("delivery.pickup_restaurant", restaurant)

        pickup_coords = fake_gps()
        dropoff_coords = fake_gps()

        # Simulate pickup delay
        pickup_delay = random.uniform(0.5, 2.0)
        time.sleep(pickup_delay)

        estimated_minutes = random.randint(10, 40)
        delivery = {
            "id": delivery_id,
            "order_id": order_id,
            "driver": driver,
            "status": "in_transit",
            "pickup": pickup_coords,
            "dropoff": dropoff_coords,
            "estimated_minutes": estimated_minutes,
        }
        deliveries[delivery_id] = delivery

        delivery_duration.record(random.uniform(10, 40), {"driver": driver})
        deliveries_counter.add(1, {"driver": driver})

        logger.info(
            "Delivery assigned",
            extra={"delivery_id": delivery_id, "order_id": order_id, "driver": driver},
        )

        # Notify customer (HTTP, synchronous)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{NOTIFICATION_SERVICE_URL}/notify",
                    json={
                        "order_id": order_id,
                        "delivery_id": delivery_id,
                        "driver": driver,
                        "message": (
                            f"Your order is on its way! Driver {driver} "
                            f"will deliver in ~{estimated_minutes} minutes."
                        ),
                    },
                )
                resp.raise_for_status()
        except Exception as exc:
            span.record_exception(exc)
            logger.warning(
                "Failed to send notification",
                extra={"order_id": order_id, "error": str(exc)},
            )

        span.set_status(trace.StatusCode.OK)
        return delivery


# ─── FastAPI App ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Delivery service starting up")

    # Start the RabbitMQ consumer as a background asyncio task
    consumer_task = asyncio.create_task(
        start_consumer(process_delivery, tracer),
        name="rabbitmq-consumer",
    )

    yield

    logger.info("Delivery service shutting down")
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    tracer_provider.shutdown()
    meter_provider.shutdown()


app = FastAPI(title="Delivery Service", lifespan=lifespan)
FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
Instrumentator().instrument(app).expose(app)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "delivery-service"}


@app.get("/deliveries/{delivery_id}")
async def get_delivery(delivery_id: str):
    delivery = deliveries.get(delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return delivery


@app.get("/deliveries")
async def list_deliveries():
    return {"total": len(deliveries), "deliveries": list(deliveries.values())}
