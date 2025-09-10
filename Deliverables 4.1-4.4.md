## 4.1 Architecture Design
### Prototype Implementation (what I built):
- Frontend (React + Vite): Simple UI for uploading PDFs and displaying classification & extracted fields.
- Backend (FastAPI): REST API with endpoints for document ingestion (/upload) and retrieval (/document/{id}). Handles PDF parsing, classification (rule-based + AI), and field extraction (AI + regex fallback).
- Database (MongoDB): Stores documents, extracted KPIs, highlights, and metadata.
- Containerization (Docker Compose): Backend, frontend, and MongoDB run as separate services, orchestrated locally with ‘docker compose up’.

### Production-ready design:
- Microservices: Split into ingestion service, classification/extraction service, and API gateway for cleaner separation of concerns.<br/>
- Scalability:
  - Deploy backend in Kubernetes with autoscaling.
  - Use managed MongoDB (e.g., Atlas) with replication for HA.
  - Offload CPU-intensive tasks (OCR, AI extraction) to async workers (Celery, RabbitMQ/Kafka).
- Reliability: API gateway + load balancer, retry policies for workers, database backups. <br/>
- Cost-awareness:
  - Use serverless functions (AWS Lambda/GCP Cloud Functions) for bursty workloads.

## 4.2 Best Practices & Uptime
### Prototype Implementation (what I built):
- Code is modular (separate classify/, extract/, ingest/).
- Regex + AI hybrid extraction for robustness.
- Containerized backend/frontend + MongoDB for reproducibility.
- Local .env file for configuration.

### Production-ready practices:
- Coding:
  - Enforce code quality with linting (flake8, black) and typing (mypy).
  - Automated unit/integration tests (pytest + GitHub Actions).
- Deployment:
  - CI/CD pipeline (GitHub Actions / GitLab CI) to build, test, and deploy containers automatically.
  - Versioned deployments with rollback capability.
- Monitoring:
  - Metrics with Prometheus + Grafana (API latency, error rates).
  - Centralized logging (ELK stack or Loki).
  - Uptime monitoring (Pingdom, Healthchecks.io).
- High availability: 
  - Kubernetes for multi-replica backend.
  - MongoDB replica set for failover.
  - Load balancer + CDN for frontend.
- Security:
  - Secrets management (Vault or cloud KMS).
  - TLS termination at ingress.
  - Role-based access control for MongoDB.

## 4.3 Lessons from Past Attempts
https://outsourcify.net/how-to-avoid-ai-project-failures-lessons-from-automation/<br/>
https://www.solvexia.com/blog/10-why-process-automation-projects-fail

### Weak/Poor Fallback Strategies
Systems relied on a single ML model for classification or extraction. When confidence dropped, they either failed silently or returned incorrect results. This was due to the lack of rule-based or heuristic fallbacks, weak confidence scoring, and no human-in-the-loop correction workflows.
Lesson learned: Hybrid pipelines (ML + rules + manual review for low-confidence cases) improve reliability.

### Lack of Observability
The failures were hard to detect until users complained.This was due to the lack of structured logging, metrics, or anomaly detection in place.
Lesson learned: Start early with implementing observability features like logs, dashboards, and alerting. Monitor extraction accuracy and pipeline latency like production-grade systems.

### Brittle Data Pipelines
Hardcoded parsing logic broke whenever doc formats slightly changed. The extractors were overfit to training samples and ignored generalization. 
Lesson learned: Use resilient NLP approaches (transformer-based models + schema-driven normalization) and modular pipelines that can adapt to new layouts.

### Weak Data Quality Handling
Systems often assumed documents were high-quality. Noisy scans or missing fields caused crashes or misclassification. This was due to lack of preprocessing (image cleaning, OCR tuning, schema validation).
Lesson learned: Build preprocessing and anomaly-detection modules that sanitize inputs before feeding them into ML models.

## 4.4 Vision Exploration
I would target the automation of ESG reporting. ESG data tends to come from diverse sources like PDF reports, sustainability statements, regulatory filings, etc, 
often in inconsistent formats. Automating the process here would mirror the notice-processing pipeline. Nowadays, global regulators increasingly require ESG 
transparency, and institutional investors must process large volumes of ESG reports, sustainability metrics, and disclosures. A tool that extracts and standardizes 
ESG KPIs (e.g., carbon footprint, board diversity, supply chain risk) will add major value to institutional investors.

