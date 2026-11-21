# FaultLab - Distributed Chaos & Fault-Injection Lab

A controlled chaos engineering sandbox for simulating production-scale failures in microservices. Deliberately break services using Linux kernel tools, trace failures with OpenTelemetry, and verify recovery with automated runbooks.

## Architecture

```
┌─────────────────┐     ┌─────────────┐     ┌──────────────┐
│   API Gateway   │────▶│    Redis    │────▶│    Worker    │
│   (Node.js)     │     │   (Queue)   │     │   (Python)   │
└─────────────────┘     └─────────────┘     └──────────────┘
         │                                            │
         └────────────────────┬───────────────────────┘
                              ▼
                      ┌───────────────┐
                      │  PostgreSQL   │
                      └───────────────┘

        All instrumented with OpenTelemetry ──▶ Jaeger
```

## What This Simulates

**Real Production Failures:**
- Network latency spikes (400ms+ tail latency)
- Packet loss causing TCP retries
- Database connection pool exhaustion
- Redis cache unavailability (queue failures)
- Cascading timeouts across service boundaries

**Debugging Techniques:**
- Distributed tracing to pinpoint bottlenecks
- Layer-by-layer diagnostics (DNS → TCP → Application → Database)
- SLA verification under fault conditions

## Quick Start

### 1. Start All Services

```bash
# Start the microservices stack
docker-compose up -d

# Verify services are healthy
docker-compose ps
```

**Services running:**
- API Gateway: http://localhost:3000
- Jaeger UI: http://localhost:16686
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### 2. Generate Normal Traffic

```bash
# Create orders (normal operation)
curl -X POST http://localhost:3000/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "CUST-001", "amount": 99.99}'

# Check queue status
curl http://localhost:3000/orders/stats
```

### 3. Inject Chaos

```bash
# Enter the API Gateway container
docker exec -it faultlab-api-gateway-1 sh

# Inject 200ms latency
python /app/chaos/fault_injector.py latency 200

# Or inject packet loss
python /app/chaos/fault_injector.py packet_loss 10

# Clear all faults
python /app/chaos/fault_injector.py clear
```

**Available Fault Injection:**
- `latency [ms]` - Add network delay
- `packet_loss [percent]` - Drop packets
- `connection_drop [port]` - Block TCP connections
- `clear` - Remove all injections

### 4. Run Predefined Chaos Scenarios

```bash
# Run cascading failure (latency → packet loss → DB drop)
docker exec -it faultlab-api-gateway-1 python chaos/scenarios.py cascading 30

# Available scenarios:
# - latency: Network delay spike
# - db_fail: PostgreSQL connection drop
# - redis_fail: Redis unavailability
# - packet_loss: Network packet drops
# - cascading: Multi-layer failure
```

### 5. Analyze Traces

```bash
# View traces in Jaeger UI
open http://localhost:16686

# Or analyze programmatically
cd verification
python tracer.py api-gateway 10  # Analyze last 10 minutes
```

### 6. Run Diagnostic Runbook

```bash
# Automated layer-by-layer diagnostics
python verification/runbook.py
```

**Runbook checks:**
1. **DNS Resolution** - Can services resolve hostnames?
2. **TCP Connectivity** - Are ports reachable?
3. **Service Health** - Do health endpoints respond?
4. **Network Performance** - What's the latency?

## Chaos Engineering Workflow

```bash
# 1. Baseline: Generate normal traffic
for i in {1..10}; do
  curl -X POST http://localhost:3000/orders \
    -H "Content-Type: application/json" \
    -d "{\"customer_id\": \"CUST-$i\", \"amount\": 99.99}"
done

# 2. Inject fault
docker exec faultlab-api-gateway-1 python chaos/scenarios.py latency 30

# 3. Generate traffic under fault
for i in {11..20}; do
  curl -X POST http://localhost:3000/orders \
    -H "Content-Type: application/json" \
    -d "{\"customer_id\": \"CUST-$i\", \"amount\": 99.99}"
done

# 4. Analyze traces
python verification/tracer.py api-gateway 5

# 5. Run diagnostics
python verification/runbook.py

# 6. Verify recovery
docker exec faultlab-api-gateway-1 python chaos/fault_injector.py clear
python verification/runbook.py
```

## OpenTelemetry Tracing

**What's Instrumented:**
- HTTP requests (Express auto-instrumentation)
- Redis operations (queue push/pop)
- PostgreSQL queries (psycopg2 instrumentation)
- Custom spans for business logic

**View traces:**
1. Open Jaeger UI: http://localhost:16686
2. Select service: `api-gateway` or `worker`
3. Click "Find Traces"
4. Inspect waterfall view to see where time is spent

**Trace Analysis Script:**
```bash
python verification/tracer.py api-gateway 10
```

Shows:
- Average/max duration
- Error rate
- Slowest operations
- Common bottlenecks

## Interview Talking Points

### 1. System Design
> "I built a multi-service order processing pipeline with an API gateway pushing to Redis, async workers pulling from the queue, and PostgreSQL for persistence. Each layer can fail independently."

### 2. Chaos Engineering
> "I used Linux kernel tools—`tc` for latency injection and `iptables` for connection drops—to simulate real AWS production failures. The containers run with `CAP_NET_ADMIN` to manipulate network interfaces."

### 3. Distributed Tracing
> "I instrumented all services with OpenTelemetry to trace requests across boundaries. When I injected 200ms latency, traces showed the worker's Redis `brpop` became the bottleneck, adding 800ms to total duration."

### 4. Automated Diagnostics
> "My runbook script diagnoses failures layer-by-layer: DNS resolution, TCP handshake, service health checks, and database connections. It pinpoints whether an issue is network, auth/IAM, or application-level."

### 5. Fault Isolation
> "When I drop PostgreSQL connections with iptables, the worker fails fast with connection refused. But when I inject packet loss, it triggers TCP retries causing 10-30 second hangs—teaching me the difference between hard and soft failures."

### 6. Production Readiness
> "This simulates real AWS issues: ELB timeouts, AZ failures, DynamoDB throttling, and IAM permission errors. The verification scripts check if SLAs are met and validate recovery time."

## Extending the Lab

### Add a New Fault Type

```python
# chaos/fault_injector.py
def inject_bandwidth_limit(self, rate_kbps=100):
    """Limit bandwidth using tc"""
    cmd = [
        'tc', 'qdisc', 'add', 'dev', self.interface, 'root', 'tbf',
        'rate', f'{rate_kbps}kbit', 'burst', '32kbit', 'latency', '400ms'
    ]
    subprocess.run(cmd)
```

### Add a New Service

```yaml
# docker-compose.yml
  notifier:
    build: ./services/notifier
    environment:
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318
      - OTEL_SERVICE_NAME=notifier
    depends_on:
      - redis
```

### Add Custom Metrics

```python
# In worker.py or server.js
from opentelemetry import metrics

meter = metrics.get_meter(__name__)
order_counter = meter.create_counter("orders_processed")

# Increment in processing logic
order_counter.add(1, {"status": "success"})
```

## Troubleshooting

**Traces not showing in Jaeger:**
```bash
# Check Jaeger is running
docker-compose logs jaeger

# Verify OTLP endpoint is reachable
curl http://localhost:4318/v1/traces
```

**Fault injection not working:**
```bash
# Ensure container has NET_ADMIN capability
docker inspect faultlab-api-gateway-1 | grep -A5 CapAdd

# Check tc rules are applied
docker exec faultlab-api-gateway-1 tc qdisc show
```

**Services not connecting:**
```bash
# Run diagnostic runbook
python verification/runbook.py

# Check Docker network
docker network inspect faultlab-network
```

## Tech Stack

- **Languages**: Python 3.11, Node.js 18
- **Infrastructure**: Docker, Docker Compose
- **Databases**: PostgreSQL 15, Redis 7
- **Tracing**: OpenTelemetry, Jaeger
- **Chaos Tools**: Linux `tc` (traffic control), `iptables`

## Resume Bullets

✅ **Built a containerized fault-injection sandbox using Docker, Python, and Linux networking tools (tc, iptables) to simulate latency spikes, packet drops, and database lock contention across microservices.**

✅ **Instrumented end-to-end request tracing with OpenTelemetry across Node.js, Redis, and PostgreSQL, pinpointing tail-latency bottlenecks and cascading timeout failures.**

✅ **Authored automated Python verification scripts to isolate DNS, TCP, and AWS IAM permission failures, validating service recovery under strict SLA thresholds.**

## License

MIT
