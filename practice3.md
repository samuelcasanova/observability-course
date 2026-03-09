# Practice 3: Mastering Jaeger & Distributed Tracing

Now that you've got the basics down with Grafana, let's switch gears and focus on distributed tracing with Jaeger. 

In a microservices architecture like ours, a single user request (like an order) crosses multiple network boundaries. Tracing is how we stitch that story together.

Here are some real-world scenarios you can investigate using Jaeger (available at http://localhost:16686). You can generate traffic by running your load script or simply curling the `order-service` API.

---

### 🚨 Challenge 1: The "10% Error Rate" Investigation 
**The Scenario:** Customer support states that some orders are failing right after they are placed, but they don't know why. We know from our Prometheus metrics that there's a 10% failure rate in the kitchen. 
**Your Task:**
1. Open up Jaeger and search for traces where the service is `kitchen-service` and specifically filter for traces that contain **errors** (Tags: `error=true`).
2. Drill into a failed trace. What is the exact exception message attached to the span? 
3. *Real world benefit: Instead of digging through endless text logs, you can jump straight to the exact line/error that caused the transaction to fail.*

### ⏳ Challenge 2: The Latency Bottleneck
**The Scenario:** A high-value customer complained that their food took way too long to reach the "In Transit" status. 
**Your Task:**
1. Search for traces from `order-service` representing the full end-to-end flow. Use the "Min Duration" filter to find traces that took longer than **6 seconds**.
2. Open a slow trace and look at the Gantt chart waterfall. 
3. Answer this: Which service was the primary bottleneck? Was it `order-service`, the actual food prep in `kitchen-service`, or the driver assignment in `delivery-service`?
4. *Real world benefit: Quickly pointing out which specific hop in the network is causing slow API responses so you can scale or optimize it.*

### 🐰 Challenge 3: Asynchronous Context Propagation (Message Queues)
**The Scenario:** Our application uses both synchronous HTTP (REST) calls and asynchronous Message Queues (RabbitMQ) to communicate.
**Your Task:**
1. Find a successful end-to-end trace (one that hits order, kitchen, delivery, and notification).
2. Look at how `order-service` talks to `kitchen-service`. You'll see an HTTP POST. 
3. Now look at how `kitchen-service` talks to `delivery-service`. You should see `publish` and `process` spans. 
4. This is called "Context Propagation". The trace ID was injected into the RabbitMQ headers and extracted by the delivery service! 
5. *Real world benefit: Confirming that background jobs and async workers aren't "breaking the chain" or creating orphaned spans.*

### 🔌 Challenge 4: The Cascading Failure
**The Scenario:** One of your dependent microservices crashes completely. How does that affect the rest of the traces?
**Your Task:**
1. Manually stop the notification service: `docker compose stop notification-service`
2. Send a few new orders to the system.
3. Find the resulting traces in Jaeger. How do they look?
4. Does the failure in the notification HTTP call crash the entire delivery process, or does the delivery still get assigned? Look at the span status for the `delivery.assign` span versus the HTTP client span.
5. *Real world benefit: Visualizing the blast radius of an outage.*

---

**Bonus Pro-tip:** To really master tracing, go to your Grafana Explore tab, switch the data source to Loki, and search for `{container="order-service"}`. Open a log line, and you should see a `trace_id` field. Now you can copy that ID and paste it directly into Jaeger to jump from a log to a trace!
