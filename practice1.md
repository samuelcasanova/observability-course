Great exercise! Here are 4 indicators to guide your practice. I'll describe what to measure and why it matters, but leave the PromQL and panel choices entirely to you.

1. 🍕 Kitchen failure rate
The kitchen service has a 10% random failure rate baked in. A meaningful indicator would express what proportion of preparation attempts are failing — not a raw count, but a ratio over time.

Think about: which metric(s) do you need to combine? What time window makes sense? What panel type communicates a ratio at a glance?

2. ⏱️ Preparation time distribution
The kitchen simulates a 1–5 second delay per order. Rather than just an average, a more honest representation captures the spread of that duration, including the worst cases.

Think about: the histogram metric that's already exposed. What Prometheus function unlocks percentile calculations from a histogram? Which percentile is most meaningful to a kitchen manager?

3. 📬 Queue depth vs. throughput
Orders flow through RabbitMQ after preparation. You can observe the relationship between how fast orders are being dispatched into the queue and how fast they're being consumed on the other side.

Think about: what signals does the delivery service produce? Is this a single panel or a combined view? How would a bottleneck appear visually?

4. 🚚 End-to-end order lifecycle
An order touches at least 3 services: order → kitchen → delivery. A high-level indicator would show the overall health of the pipeline — are orders making it all the way through, or accumulating/failing at a specific stage?

Think about: how would you compare counters across different services? What does it mean if the rate of orders entering the kitchen is much higher than the rate leaving it?

Good luck! Once you've had a go, feel free to share what you built and we can review it together.