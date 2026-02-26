import winston from "winston";
import { trace, context } from "@opentelemetry/api";

// Custom format that injects active trace_id and span_id into every log line
const otelFormat = winston.format((info) => {
  const activeSpan = trace.getActiveSpan();
  if (activeSpan) {
    const ctx = activeSpan.spanContext();
    info.trace_id = ctx.traceId;
    info.span_id = ctx.spanId;
  }
  return info;
});

export const logger = winston.createLogger({
  level: process.env.LOG_LEVEL?.toLowerCase() || "info",
  format: winston.format.combine(
    otelFormat(),
    winston.format.timestamp(),
    winston.format.json(),
  ),
  transports: [new winston.transports.Console()],
});
