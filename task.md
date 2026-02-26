# Food Delivery Tracker — Task Checklist

## Phase 1: Planning
- [/] Write implementation plan
- [ ] Get user approval

## Phase 2: Project Scaffolding
- [ ] Create repo structure & Docker Compose skeleton
- [ ] Add shared `.env` and config files

## Phase 3: Services
- [ ] **Order Service** (Python / FastAPI)
- [ ] **Kitchen Service** (Node.js / Express)
- [ ] **Delivery Service** (Python / FastAPI)
- [ ] **Notification Service** (Node.js / Express)

## Phase 4: Observability Stack
- [ ] OpenTelemetry instrumentation in all services
- [ ] Prometheus metrics endpoints
- [ ] Structured JSON logging (all services)
- [ ] Docker Compose: Jaeger, Prometheus, Grafana, Loki

## Phase 5: Data Simulation
- [ ] Seed script / loop to generate realistic order traffic

## Phase 6: Verification
- [ ] End-to-end trace visible in Jaeger
- [ ] Metrics visible in Grafana
- [ ] Logs visible in Loki / Grafana
