# Mac Observability Stack: Event-Driven Local Telemetry

An event-driven macOS telemetry agent that bridges local workspace activity to a containerized, stateful LGTM (Loki, Grafana, Tempo, Mimir) observability stack.

This project tracks granular developer productivity metrics, OS-level window transitions, and deep-linked browser contexts. It replaces traditional, CPU-heavy polling scripts with a producer-consumer architecture, pushing structured JSON metadata to a local Dockerized backend for LogQL/PromQL aggregation.

---

## 🏗 System Architecture

The pipeline is strictly decoupled into three layers: **Data Ingestion (Agent)**, **Storage (Docker Stack)**, and **Visualization (Grafana)**.

* **Producer:** A macOS `LaunchAgent` running a Python observer via native OS hooks.
* **Transport:** Asynchronous HTTP POST streams containing structured JSON payloads.
* **Consumer & Storage:** Grafana Loki (Log Stream Engine) and Mimir (Metrics Engine).
* **State Management:** Docker Volumes ensure dashboard configurations and data sources survive container teardowns.

---

## ⚙️ Core Components

### 1. The Event-Driven Agent (`monitor.py`)

This agent utilizes an **Observer Pattern** via Apple's native `AppKit` and `NSWorkspace` frameworks to achieve zero-idle CPU overhead.

* **Non-Blocking Telemetry:** The script listens for `NSWorkspaceDidActivateApplicationNotification`. It remains entirely dormant until the macOS kernel explicitly broadcasts a window-switch event.
* **Contextual Deep-Inspection:** If the activated application is Google Chrome, the agent spawns an asynchronous AppleScript process to extract the active tab's URL, cross-referencing it against a categorical mapping dictionary (e.g., Engineering, Education, Communication).
* **Structured Logging:** Utilizes `python-logging-loki` to emit structured JSON payloads. Logs are decorated with explicitly defined metadata tags (`app`, `category`, `site`, `uptime_sec`), treating logs as highly queryable dimensions rather than flat text.

### 2. The Observability Backend (`docker-compose.yaml`)

The infrastructure is containerized, declarative, and designed for local isolation.

* **Grafana Loki (Port 3100):** Acts as the primary log aggregation system. Highly efficient, indexing only the metadata labels attached by the Python agent.
* **Grafana Mimir (Port 9009):** The long-term storage backend for Prometheus metrics, configured to track high-resolution state transitions.
* **Grafana (Port 3000):** The visualization layer, configured with anonymous admin access and a permanent Docker Volume (`grafana_data`) for stateful dashboard persistence.

### 3. The OS Integration (`launchctl`)

To ensure the pipeline runs as a resilient background daemon, the agent is bootstrapped into the macOS kernel as a user-scoped `LaunchAgent`.

* **Lifecycle Management:** A `.plist` configuration dictates the daemon's behavior, automatically reviving the process on login or failure.
* **Decoupled Output Routing:** `stdout` and `stderr` are piped into `/tmp/mac_monitor.*.log` for out-of-band debugging, keeping the primary observability pipeline immune to internal script exceptions.

---

## 🚀 Quickstart & Deployment

### Prerequisites

* macOS (M-Series or Intel)
* Docker Desktop
* Python 3.10+ (`.venv` recommended)

### 1. Stand Up the Infrastructure

Spin up the containerized observability stack with persistent volumes.

```bash
docker-compose up -d
```

Wait for Loki's ingester ring to synchronize and unlock (approx 15s):

```bash
while true; do
  curl -s http://127.0.0.1:3100/ready
  echo ""
  sleep 2
done
```

### 2. Initialize the Python Agent

Install the required macOS bridging libraries and initialize the virtual environment.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Register the Background Daemon

Modify the absolute paths in `com.sravani.monitor.plist` to match your local repository structure, then bootstrap the agent:

```bash
# Load the agent into the user session
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.sravani.monitor.plist

# To force-restart the agent after code modifications:
launchctl kickstart -k gui/$(id -u)/com.sravani.monitor
```

---

## 📊 Dashboard Configuration & Data Sources

Because Grafana runs within an isolated Docker network, data sources must be configured using Docker's internal DNS resolver rather than `localhost`.

### 1. Configure Data Sources

Navigate to `http://localhost:3000` → **Connections** → **Data Sources**:

* **Loki:** Set the URL to `http://loki:3100`
* **Mimir (Prometheus):** Set the URL to `http://mimir:9009/prometheus`
* **Note on Multitenancy:** Mimir requires a Tenant ID. Under **HTTP Headers**, add `X-Scope-OrgID` with a value of `mac_monitor`

### 2. Primary LogQL/PromQL Queries

Create a new dashboard and apply the following queries to visualize the telemetry stream.

#### Focus Distribution (Pie Chart)

```logql
sum by (category) (
  count_over_time({job="mac_monitor", category!=""}[1h])
)
```

#### Activity Chronology (Time Series)

```logql
sum by (app) (
  count_over_time({job="mac_monitor", app!=""}[1m])
)
```

> Set Legend to `{{app}}`

#### Top Targets (Bar Gauge)

```logql
sum by (app) (
  count_over_time({job="mac_monitor", app!=""}[12h])
)
```

#### Live Tail (Logs)

```logql
{job="mac_monitor"}
```

---

## 🛠 Handled Edge Cases & Resiliency

### Mitigating Race Conditions

The Python agent and Docker backend are decoupled. If the `launchctl` agent fires before Loki is ready (`Connection Refused [Errno 61]`), the script will gracefully fail and restart via macOS daemon policies until the Loki API is responsive.

### Schema Mutability Protection

Ensuring consistent label payloads across window transitions prevents Loki from throwing `HTTP 400 Bad Request` errors due to sudden stream index mutations.

### Volume Persistence

Running `docker-compose down` destroys the containers but preserves the `grafana_data` volume, ensuring visualization configurations are immutable across teardowns.
