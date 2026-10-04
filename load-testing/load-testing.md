## Load Testing

Load tested with [k6](https://k6.io/) against a local Docker Compose setup
(FastAPI + Kafka + Postgres, single machine). Scripts live in `load-testing/load-testing-scripts`.

### 1. Webhook response time: Kafka offload vs. synchronous DB write

**What this tests:** `/webhook-payload` (production path) hands the payload to
Kafka and replies immediately. `/webhook-db` (test-only route, not used in the
actual flow) does the same parsing and a synchronous Postgres insert inside the
request before replying. Comparing the two isolates the effect of offloading
the DB write onto an async pipeline.

**Method:** same saved GitHub push payload (`payload.json`) sent to both endpoints, fixed
request rate (`constant-arrival-rate`), 30s per run, at 20 req/s and 100 req/s.

| Rate | Endpoint | p50 | p90 | p95 | Failed |
|---|---|---|---|---|---|
| 20 req/s | Kafka offload | 2.18ms | 3.04ms | 3.95ms | 0% |
| 20 req/s | Direct DB write | 5.23ms | 6.74ms | 8.52ms | 0% |
| 100 req/s | Kafka offload | 2.63ms | 3.72ms | 4.87ms | 0% |
| 100 req/s | Direct DB write | 5.24ms | 6.44ms | 8.85ms | 0% |

**Result:** Kafka offload is consistently 1.8-2.2x faster (p95) than a
synchronous write, with zero failed requests on either path at both rates.

Full k6 HTML reports:
- [report_kafka_20rps.html](./load-testing-reports/report_kafka_20rps.html)
- [report_db_20rps.html](./load-testing-reports/report_db_20rps.html)
- [report_kafka_100rps.html](./load-testing-reports/report_kafka_100rps.html)
- [report_db_100rps.html](./load-testing-reports/report_db_100rps.html)

**Note:** tested against a near-empty local Postgres table. In production,
with the database under real concurrent load (other queries, larger tables),
the gap would likely widen further, since the Kafka path's latency doesn't
depend on database load at all, while the direct-write path's does.

### 2. Crash / duplicate-delivery test

**What this tests:** the consumer writes to Postgres, then commits the Kafka
offset, as two separate steps. If the consumer crashes between them, Kafka has
no record the message was processed and redelivers it on restart, risking a
duplicate row.

**Method:** sent a burst of webhook events via k6, each tagged with a unique
test ID, to `/webhook-payload`. Killed the consumer process (`docker kill`)
mid-burst to simulate a hard crash, then restarted it. To reliably land the
kill inside the normally sub-millisecond vulnerable window, a temporary
2-second delay was added between the DB commit and the Kafka offset commit for
this test only, then removed afterward.

**Before fix:**

| Metric | Value |
|---|---|
| Events sent | 20 |
| Rows landed | 21 |
| Duplicates | 1 (same event inserted twice) |

**Fix:** added a unique constraint on `delivery_id`, populated from GitHub's
`X-GitHub-Delivery` header (unique per webhook delivery, including retries).
The consumer now catches the resulting `IntegrityError`, rolls back that one
insert, and still commits the Kafka offset, so a replayed message is skipped
instead of crashing the consumer or retrying forever. Existing rows that
predate this change have `delivery_id = NULL`, since they were never assigned
one; new events are deduplicated going forward.

**After fix (identical test, same crash timing):**

| Metric | Value |
|---|---|
| Events sent | 20 |
| Rows landed | 20 |
| Duplicates | 0 |
