# Enterprise AI Travel Agent - Microservices Architecture

An enterprise-grade travel booking platform powered by AI, built with a microservices architecture. Features intelligent itinerary generation, payment processing, fraud detection, and comprehensive observability.

![Python](https://img.shields.io/badge/python-3.10-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green)
![AWS](https://img.shields.io/badge/AWS-EKS-orange)
![Kubernetes](https://img.shields.io/badge/kubernetes-1.28-blue)
![Microservices](https://img.shields.io/badge/architecture-microservices-brightgreen)

---

## Overview

This application transforms a simple travel itinerary generator into a production-ready, enterprise-grade system using microservices architecture. It demonstrates industry best practices including:

- Service-oriented architecture with 7 microservices
- Synchronous and asynchronous communication patterns
- Event-driven analytics
- Fraud detection in payment processing
- Message queue-based notifications
- Comprehensive observability with ELK stack
- Automated load testing

---

## Architecture

### High-Level Architecture

```
Streamlit UI (Frontend) ────────┐
                                ↓
Internet → API Gateway → Booking Service → Payment Service → Fraud Service
                ↓                                    ↓
         Analytics Service                    RabbitMQ Queue
                                                     ↓
                                          Notification Service

                            Client Simulator (Load Testing)
```

### Microservices Overview

| Service | Port | Purpose | Dependencies |
|---------|------|---------|--------------|
| **Gateway Service** | 8000 | API Gateway, request routing | Booking, Analytics |
| **Booking Service** | 8001 | Itinerary creation, booking management | Payment, Groq LLM |
| **Payment Service** | 8002 | Payment processing | Fraud, RabbitMQ |
| **Fraud Service** | 8003 | Fraud detection and risk scoring | None |
| **Notification Service** | 8004 | Async notifications (email/SMS/push) | RabbitMQ |
| **Analytics Service** | 8005 | Event tracking and analytics | None |
| **Client Simulator** | N/A | Automated load testing | Gateway |
| **Streamlit UI** | 8501 | Web frontend for users | Gateway |

**Supporting Infrastructure**:
- **RabbitMQ**: Message broker for async communication
- **Supabase**: PostgreSQL database with RLS
- **ELK Stack**: Logging and monitoring
- **AWS EKS**: Kubernetes orchestration

**Detailed Architecture**: See [MICROSERVICES_ARCHITECTURE.md](MICROSERVICES_ARCHITECTURE.md)

---

## Features

### Functional Features
- AI-powered travel itinerary generation (Groq LLM)
- User account management
- Booking and payment processing
- Real-time fraud detection
- Automated notifications
- Comprehensive analytics and reporting

### Technical Features
- RESTful API design
- Service-to-service communication (HTTP)
- Asynchronous messaging (RabbitMQ)
- Database persistence with RLS
- Structured JSON logging
- Health checks and probes
- Horizontal scalability
- Container orchestration

---

## Prerequisites

### Required Accounts
- **AWS Account** with EKS access
- **Supabase Account** (free tier works)
- **Groq API Key** (free tier available)

### Required Tools
- Docker
- kubectl (v1.28+)
- eksctl
- AWS CLI (configured)
- curl/httpie (for testing)

### EKS Cluster
```bash
eksctl create cluster \
  --name ai-travel-agent \
  --region ap-south-1 \
  --node-type t3.medium \
  --nodes 2 \
  --managed
```

---

## Quick Start

### 1. Set Environment Variables

```bash
export GROQ_API_KEY="your_groq_api_key"
export SUPABASE_URL="https://xxxxx.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="your_service_role_key"
export AWS_REGION="ap-south-1"
```

### 2. Deploy Microservices

```bash
chmod +x deploy-microservices.sh
./deploy-microservices.sh
```

This script will:
- Create ECR repositories
- Build and push Docker images
- Deploy RabbitMQ
- Deploy all microservices
- Deploy client simulator

### 3. Deploy Streamlit Frontend

```bash
# Build and push Streamlit image
docker build -t streamlit-app:latest .
docker tag streamlit-app:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/streamlit-app:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/streamlit-app:latest

# Deploy to Kubernetes
kubectl apply -f k8s-deployment.yaml
```

### 4. Access the Application

```bash
# Get Streamlit UI URL
kubectl get svc streamlit-service
STREAMLIT_URL=$(kubectl get svc streamlit-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "Streamlit UI: http://$STREAMLIT_URL"

# Get Gateway API URL (optional - for direct API access)
kubectl get svc gateway-service
GATEWAY_URL=$(kubectl get svc gateway-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "Gateway API: http://$GATEWAY_URL"
```

---

## Usage

### Option 1: Streamlit Web UI (Recommended for Users)

1. **Access the UI**:
   ```
   http://<STREAMLIT_URL>
   ```

2. **Login**: Enter your email and name in the sidebar

3. **Create Itinerary** (Tab 1):
   - Enter city: "Paris"
   - Enter interests: "museums, art, wine"
   - Click "Generate Itinerary"
   - View AI-generated itinerary

4. **Book Trip** (Tab 2):
   - Review itinerary preview
   - Select payment method
   - Agree to terms and conditions
   - Click "Complete Booking"
   - View booking confirmation and fraud check results

5. **View Bookings** (Tab 3):
   - See all your bookings
   - Expand for details
   - Click "View Full Details" for complete data

For complete frontend documentation, see [FRONTEND_GUIDE.md](FRONTEND_GUIDE.md)

---

### Option 2: Direct API Access (For Developers)

## API Usage Examples

### Create Itinerary

```bash
curl -X POST http://$GATEWAY_URL/api/itineraries \
  -H "Content-Type: application/json" \
  -d '{
    "city": "Paris",
    "interests": "museums, art, wine",
    "user_email": "test@example.com",
    "user_name": "Test User"
  }'
```

Response:
```json
{
  "itinerary_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "city": "Paris",
  "content": "Day Trip Itinerary for Paris:\n\n9:00 AM - Visit the Louvre Museum...",
  "status": "draft"
}
```

### Create Booking

```bash
curl -X POST http://$GATEWAY_URL/api/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "itinerary_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440001",
    "payment_method": "credit_card"
  }'
```

Response:
```json
{
  "booking_id": "550e8400-e29b-41d4-a716-446655440002",
  "payment_id": "550e8400-e29b-41d4-a716-446655440003",
  "status": "confirmed",
  "fraud_check": {
    "fraud_check_id": "550e8400-e29b-41d4-a716-446655440004",
    "risk_score": 25.5,
    "status": "approved",
    "reason": "No risk factors detected"
  }
}
```

### Get Booking Details

```bash
curl http://$GATEWAY_URL/api/bookings/{booking_id}
```

---

## Service Flow Diagrams

### Booking Flow

```
1. User → Gateway: POST /api/bookings
2. Gateway → Booking Service: Create booking
3. Booking Service → Payment Service: Process payment
4. Payment Service → Fraud Service: Check fraud
5. Fraud Service → Payment Service: Risk score
6. Payment Service → RabbitMQ: Publish notification
7. Notification Service ← RabbitMQ: Consume notification
8. Notification Service → Supabase: Save notification
9. Payment Service → Booking Service: Payment result
10. Booking Service → Gateway: Booking result
11. Gateway → Analytics Service: Track event
12. Gateway → User: Final response
```

---

## Project Structure

```
GCP_ELK_Capstone/
├── services/
│   ├── shared/                    # Shared utilities
│   │   ├── database.py           # Supabase client
│   │   ├── logger.py             # Structured logging
│   │   ├── message_broker.py    # RabbitMQ client
│   │   └── models.py             # Pydantic models
│   │
│   ├── gateway/                   # API Gateway
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── booking/                   # Booking Service
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── payment/                   # Payment Service
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── fraud/                     # Fraud Detection Service
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── notification/              # Notification Service
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── analytics/                 # Analytics Service
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   └── client-simulator/          # Load Testing
│       ├── main.py
│       ├── requirements.txt
│       └── Dockerfile
│
├── k8s/                           # Kubernetes manifests
│   ├── rabbitmq.yaml
│   ├── gateway-service.yaml
│   ├── booking-service.yaml
│   ├── payment-service.yaml
│   ├── fraud-service.yaml
│   ├── notification-service.yaml
│   ├── analytics-service.yaml
│   └── client-simulator.yaml
│
├── Legacy (Monolith):
│   ├── app.py                     # Original Streamlit app
│   ├── src/                       # Original source code
│   ├── k8s-deployment.yaml       # Original deployment
│   ├── elasticsearch.yaml
│   ├── logstash.yaml
│   ├── kibana.yaml
│   └── filebeat.yaml
│
├── Documentation:
│   ├── README.md                  # This file
│   ├── MICROSERVICES_ARCHITECTURE.md
│   ├── MICROSERVICES_DEPLOYMENT_GUIDE.md
│   ├── AWS_DEPLOYMENT_GUIDE.md   # Legacy deployment
│   ├── ARCHITECTURE.md            # Legacy architecture
│   └── deploy-microservices.sh
│
└── Database:
    └── Migration applied to Supabase
```

---

## Monitoring & Observability

### Health Checks

```bash
kubectl get pods -l app=gateway-service -o name | head -1 | \
  xargs kubectl exec -it -- curl localhost:8000/health
```

All services expose `/health` endpoint returning:
```json
{"status": "healthy", "service": "<service-name>"}
```

### View Logs

```bash
kubectl logs -l app=gateway-service --tail=100 -f
kubectl logs -l app=booking-service --tail=100 -f
kubectl logs -l app=payment-service --tail=100 -f
```

### ELK Stack (if deployed)

Access Kibana on port 30601:
```bash
kubectl get nodes -o wide
```

Open: `http://<NODE_IP>:30601`

Filter logs by service:
```
kubernetes.labels.app: "gateway-service"
```

### RabbitMQ Management UI

```bash
kubectl port-forward svc/rabbitmq 15672:15672
```

Open: http://localhost:15672 (guest/guest)

### Analytics Dashboard

```bash
kubectl get pods -l app=analytics-service -o name | head -1 | \
  xargs kubectl exec -it -- curl localhost:8005/analytics/summary?days=7
```

---

## Testing

### Manual Testing

See API examples above.

### Automated Load Testing

The client simulator runs continuously, generating realistic user traffic:

```bash
kubectl logs -l app=client-simulator --tail=50 -f
```

You should see logs like:
```
{"timestamp": "2026-03-01T10:30:00Z", "service": "client-simulator", "level": "INFO", "message": "User 5 creating itinerary for Tokyo"}
{"timestamp": "2026-03-01T10:30:05Z", "service": "client-simulator", "level": "INFO", "message": "User 5 completed booking: abc-123, Status: confirmed"}
```

### Verify Database

Check Supabase dashboard:
```sql
SELECT COUNT(*) FROM bookings;
SELECT COUNT(*) FROM payments;
SELECT COUNT(*) FROM fraud_checks;
SELECT COUNT(*) FROM notifications;
SELECT COUNT(*) FROM analytics_events;
```

---

## Scaling

### Manual Scaling

```bash
kubectl scale deployment gateway-service --replicas=5
kubectl scale deployment booking-service --replicas=3
```

### Auto-scaling (HPA)

```bash
kubectl autoscale deployment gateway-service \
  --cpu-percent=70 \
  --min=2 \
  --max=10
```

---

## Cost Estimate

| Component | Monthly Cost (ap-south-1) |
|-----------|--------------------------|
| EKS Control Plane | $73 |
| 2x t3.medium nodes | $60 |
| LoadBalancer | $18 |
| ECR Storage (~2GB) | $0.20 |
| EBS (ELK + RabbitMQ) | $1 |
| **Microservices Total** | **~$152/month** |

Add ~$3-5/month if keeping original monolith deployed.

---

## Troubleshooting

### Pods Not Starting

```bash
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

Common issues:
- Image pull errors (check ECR permissions)
- Missing secrets
- Service dependencies not ready

### Service Communication Errors

```bash
kubectl exec -it <pod-name> -- nslookup booking-service
kubectl exec -it <pod-name> -- curl http://booking-service:8001/health
```

### RabbitMQ Connection Issues

```bash
kubectl logs -l app=rabbitmq
kubectl logs -l app=notification-service | grep -i rabbitmq
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [COMPLETE_SYSTEM_OVERVIEW.md](COMPLETE_SYSTEM_OVERVIEW.md) | Complete system guide with all components |
| [FRONTEND_GUIDE.md](FRONTEND_GUIDE.md) | Streamlit UI documentation and usage |
| [MICROSERVICES_ARCHITECTURE.md](MICROSERVICES_ARCHITECTURE.md) | Backend architecture details |
| [MICROSERVICES_DEPLOYMENT_GUIDE.md](MICROSERVICES_DEPLOYMENT_GUIDE.md) | Step-by-step deployment |
| [MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md) | Monolith to microservices migration |
| [ELK_ACCESS_GUIDE.md](ELK_ACCESS_GUIDE.md) | Log viewing with Kibana |
| [AWS_DEPLOYMENT_GUIDE.md](AWS_DEPLOYMENT_GUIDE.md) | Legacy monolith deployment |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Legacy architecture |

---

## Migration from Monolith

The original Streamlit monolith is preserved in the repository. Key changes:

**Before (Monolith)**:
- Single Streamlit application
- Direct LLM calls
- No payment processing
- No fraud detection
- Basic logging

**After (Microservices)**:
- 7 independent services
- RESTful APIs
- Complete booking flow with payment
- Fraud detection
- Async notifications
- Event-driven analytics
- Message queue
- Production-ready observability

---

## Security

- Row Level Security on all database tables
- Kubernetes secrets for sensitive data
- Service-to-service authentication via service role
- Internal services not exposed externally
- TLS termination at LoadBalancer (recommended in production)

---

## License

MIT License

---

## Author

Balaji Krishnan

---

## Acknowledgments

- [Groq](https://groq.com) - Fast LLM inference
- [FastAPI](https://fastapi.tiangolo.com) - Modern web framework
- [Supabase](https://supabase.com) - Database and auth platform
- [RabbitMQ](https://www.rabbitmq.com) - Message broker
- AWS - Cloud infrastructure
- Elastic - ELK stack components

---

**Enterprise-Ready Travel Booking Platform**
