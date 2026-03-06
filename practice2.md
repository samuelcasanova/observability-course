Practice 2: Interoperability & Dynamic Insights
I've created a new guide for you here: 

practice2.md

🔗 Data Links (The "Drill-Down"): Configure a Data Link on your "95th Percentile" panel. When you click a data point, it should open the Jaeger UI pre-filtered for that service and time range.

🏷️ Dashboard Variables: Your dashboard is currently "all-or-nothing." Add a variable called $service that pulls unique values from your metrics. Use this variable in your PromQL queries so you can toggle the entire dashboard between order-service, kitchen-service, etc.

💎 Exemplars (The "Holy Grail"): OpenTelemetry automatically attaches Trace IDs to your Prometheus metrics. Learn how to enable "Exemplars" in your Grafana panels. This allows you to see specific "dots" on your latency graphs that, when hovered over, show a Trace ID you can click to jump straight to that specific slow request.

📉 Recording Rules: That kitchen failure rate query is getting complex. Move that logic into a Prometheus Recording Rule. This makes Prometheus calculate the ratio every 15s in the background, so Grafana only has to query a single pre-calculated metric like kitchen:failure_rate:5m.