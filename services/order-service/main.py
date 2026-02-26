import logging
import os
import random
import time
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_fastapi_instrumentator import Instrumentator
from pythonjsonlogger import jsonlogger

from models import Order, OrderRequest, OrderStatus

# ─── Logging ──────────────────────────────────────────────────────────────────
logger = logging.getLogger("order-service")
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
resource = Resource.create({"service.name": os.getenv("OTEL_SERVICE_NAME", "order-service")})
tracer_provider = TracerProvider(resource=resource)
otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
    insecure=True,
)
tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer("order-service")

HTTPXClientInstrumentor().instrument()

# ─── In-Memory Store ───────────────────────────────────────────────────────────
orders: dict[str, Order] = {}

KITCHEN_SERVICE_URL = os.getenv("KITCHEN_SERVICE_URL", "http://localhost:3001")

RESTAURANTS = ["Bella Napoli", "Sushi Garden", "Burger Palace", "Taco Fiesta"]
ITEMS_POOL = ["Margherita", "Salmon Roll", "Double Bacon", "Burrito", "Tiramisu", "Miso Soup"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Order service starting up")
    yield
    logger.info("Order service shutting down")
    tracer_provider.shutdown()


app = FastAPI(title="Order Service", lifespan=lifespan)

FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
Instrumentator().instrument(app).expose(app)


# ─── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "order-service"}


@app.post("/orders", response_model=Order, status_code=201)
async def create_order(request: OrderRequest):
    order_id = str(uuid.uuid4())[:8]

    with tracer.start_as_current_span("order.create") as span:
        span.set_attribute("order.id", order_id)
        span.set_attribute("order.restaurant", request.restaurant)
        span.set_attribute("order.items_count", len(request.items))

        order = Order(
            id=order_id,
            restaurant=request.restaurant,
            items=request.items,
            customer=request.customer,
            status=OrderStatus.RECEIVED,
        )
        orders[order_id] = order

        logger.info(
            "Order created",
            extra={"order_id": order_id, "restaurant": request.restaurant, "customer": request.customer},
        )

        # Simulate brief processing delay
        time.sleep(random.uniform(0.05, 0.3))

        # Forward to kitchen (fire-and-forget style using background task)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {"order_id": order_id, "restaurant": request.restaurant, "items": request.items}
                resp = await client.post(f"{KITCHEN_SERVICE_URL}/prepare", json=payload)
                resp.raise_for_status()
                order.status = OrderStatus.PREPARING
                logger.info("Order sent to kitchen", extra={"order_id": order_id})
        except Exception as exc:
            order.status = OrderStatus.FAILED
            span.record_exception(exc)
            span.set_status(trace.StatusCode.ERROR, str(exc))
            logger.error("Failed to send order to kitchen", extra={"order_id": order_id, "error": str(exc)})

        orders[order_id] = order
        return order


@app.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: str):
    order = orders.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.get("/orders")
async def list_orders():
    return {"total": len(orders), "orders": list(orders.values())}
