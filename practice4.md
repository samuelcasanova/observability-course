# Practice 4: Mastering Loki & Centralized Logging

Now that you've conquered metrics with Prometheus/Grafana and distributed tracing with Jaeger, let's bring it all together with centralized logging using Loki and Promtail.

Our microservices are configured to output structured JSON logs. If you look at the code, you'll see we inject `trace_id` and specific business fields like `order_id` directly into the logs.

Here are some real-world logging scenarios to investigate using the Grafana **Explore** tab (make sure to switch your data source to **Loki**).

---

### 🕵️ Challenge 1: The Needle in the Haystack (Finding a specific order)
**The Scenario:** A customer calls support about a specific order (e.g., you can generate one or grab an `order_id` from the Jaeger UI). You need to see everything that happened to that order across *all* services.
**Your Task:**
1. In Grafana Explore -> Loki, write a query that searches across all our containers for that specific order ID. 
2. Since our logs are JSON, try using the `| json` parser to extract fields, and then filter by the `order_id`. Example structure: `{container=~".*-service"} | json | order_id="<your-order-id>"`
3. *Real world benefit: Distributed systems make looking at local server logs impossible. Centralized, structured searching is the only way to track a single transaction across multiple applications.*

{service=~".+"} | json | order_id="87a163dc"

### 🔗 Challenge 2: Log-to-Trace Correlation
**The Scenario:** You found an `ERROR` log in the `kitchen-service` indicating a failure to prepare an order, but you need to see the "big picture" of the entire request.
**Your Task:**
1. Query specifically for errors in the kitchen service: `{container="kitchen-service"} | json | level="ERROR"`.
2. Expand the log details. You'll notice a `trace_id` field! This was automatically injected by our Python logging filter using OpenTelemetry context.
3. Copy that `trace_id`, open a new Explore tab with Jaeger as the data source (or open the Jaeger UI directly), and query for that Trace ID. 
4. *Real world benefit: Logs give you the exact error exception, but traces give you the full context of the user request. Seamlessly jumping from a log to a trace is the holy grail of observability.*

Full text search:
{service=~".+"} |= "ERROR" --> case sensitive
{service=~".+"} |~ "(?i)error" --> regex, case insensitive

### 📊 Challenge 3: Extracting Metrics from Logs
**The Scenario:** You want to build a Grafana dashboard panel showing the number of failed orders, but the developers didn't add a Prometheus metric for it! All you have are the `ERROR` logs.
**Your Task:**
1. Use LogQL to calculate the rate of error logs over time. 
2. Hint: In Loki, you can use aggregation operators just like in Prometheus. Try wrapping your query in a `rate(...)` function and grouping it over time: `rate({container="order-service"} | json | level="ERROR" [5m])`.
3. *Real world benefit: If you are missing a metric during an incident, logs can be parsed and counted to create one dynamically without changing a single line of code!*

rate({service=~".+"} |~ "(?i)error"[5m])

### 🧹 Challenge 4: Noise Reduction
**The Scenario:** The `order-service` is outputting way too many `INFO` logs (like "Order service starting up" or routine lifecycle logs) that are burying the important warnings and errors.
**Your Task:**
1. Write a LogQL query for the `order-service` that *excludes* all `INFO` level logs, displaying only `WARN` and `ERROR`.
2. Hint: Use the `!=` operator after parsing the JSON: `| json | level != "INFO"`.
3. *Real world benefit: During a high-stress incident, filtering out the "happy path" noise is a critical skill to find the root cause quickly.*

{service=~".+"} | json | level != "INFO"

---

Good luck! Feel free to share your LogQL queries once you've figured them out.
