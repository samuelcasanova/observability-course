# 🍕 Food Delivery Tracker — Observability Learning Project

A minimal 4-service food delivery simulation designed to generate rich **distributed traces**, **metrics**, and **structured logs** for learning observability with OpenTelemetry, Jaeger, Prometheus, Loki, and Grafana.

## Architecture

```
Order Service (Python) ──HTTP──► Kitchen Service (Node.js) ──RabbitMQ──► Delivery Service (Python) ──HTTP──► Notification Service (Node.js)
```

- `Order → Kitchen` — synchronous HTTP (immediate response needed)
- `Kitchen → Delivery` — **async via RabbitMQ** (`orders.ready` queue, W3C trace context in message headers)
- `Delivery → Notification` — synchronous HTTP

This mix of sync and async communication is intentional: it lets you observe how distributed traces cross async boundaries.

## Services

| Service | Language | Port | Description |
|---|---|---|---|
| `order-service` | Python / FastAPI | `8000` | Creates orders, triggers the chain |
| `kitchen-service` | Node.js / Express | `3001` | Simulates food prep (10% random failure) |
| `delivery-service` | Python / FastAPI | `8001` | Assigns driver, simulates GPS |
| `notification-service` | Node.js / Express | `3002` | Logs notifications (trace log sink) |

## Observability Stack

| Tool | URL | Purpose |
|---|---|---|
| **Jaeger** | http://localhost:16686 | Distributed traces |
| **Prometheus** | http://localhost:9090 | Metrics |
| **RabbitMQ** | http://localhost:15672 | Queue management UI (guest/guest) |
| **Grafana** | http://localhost:3000 | Unified dashboards (no login required) |

> Grafana is pre-provisioned with Jaeger, Prometheus, and Loki datasources.

## Quick Start

```bash
# 1. Start everything
docker compose up -d

# 2. Wait for services to be healthy (~30 seconds)
docker compose ps

# 3. Generate traffic
python simulator/simulate.py --rate 2

# 4. Explore
#   Traces → http://localhost:16686
#   Metrics → http://localhost:9090
#   Logs + Dashboards → http://localhost:3000
```

## Key Observability Patterns

- **Distributed trace across all 4 services** — 3 HTTP hops + 1 async AMQP hop
- **Async trace propagation** — W3C `traceparent` injected into RabbitMQ message headers by Kitchen (PRODUCER span), extracted by Delivery (CONSUMER span)
- **Error spans** — Kitchen Service fails ~10% of orders
- **Custom metrics** — preparation duration histogram, delivery counter
- **Log ↔ Trace correlation** — `trace_id` injected into every JSON log line
- **Queue depth metric** — visible in RabbitMQ management UI and scrapeable via Prometheus

## Project Structure

```
observability-course/
├── docker-compose.yml
├── .env
├── services/
│   ├── order-service/        # Python / FastAPI
│   ├── kitchen-service/      # Node.js / Express
│   ├── delivery-service/     # Python / FastAPI
│   └── notification-service/ # Node.js / Express
├── observability/
│   ├── otel-collector-config.yml
│   ├── prometheus.yml
│   ├── promtail-config.yml
│   └── grafana/provisioning/
└── simulator/simulate.py
```

## Useful Commands

```bash
# View logs for all services
docker compose logs -f order-service kitchen-service delivery-service notification-service

# Restart a single service (after code change)
docker compose up -d --build order-service

# Stop everything
docker compose down

# Send a single order manually
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{"restaurant": "Bella Napoli", "items": ["Margherita"], "customer": "Alice"}'
```
