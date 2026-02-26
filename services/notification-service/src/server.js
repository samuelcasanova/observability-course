// OTel MUST be first
import "./tracing.js";

import express from "express";
import { collectDefaultMetrics, Counter, register } from "prom-client";
import { logger } from "./logger.js";

const app = express();
app.use(express.json());

collectDefaultMetrics({ prefix: "notification_" });

const notificationCounter = new Counter({
  name: "notifications_sent_total",
  help: "Total notifications sent",
  labelNames: ["channel"],
});

app.get("/health", (_req, res) => {
  res.json({ status: "ok", service: "notification-service" });
});

app.get("/metrics", async (_req, res) => {
  res.set("Content-Type", register.contentType);
  res.end(await register.metrics());
});

app.post("/notify", (req, res) => {
  const { order_id, delivery_id, driver, message } = req.body;

  // In a real system this would send an email/SMS/push.
  // Here we simply log it — the point is to show logs correlating with traces.
  logger.info("Notification dispatched", {
    order_id,
    delivery_id,
    driver,
    channel: "log",
    message,
  });

  notificationCounter.inc({ channel: "log" });

  res.json({ status: "sent", order_id });
});

const PORT = process.env.PORT || 3002;
app.listen(PORT, () => {
  logger.info(`Notification service listening on port ${PORT}`);
});
