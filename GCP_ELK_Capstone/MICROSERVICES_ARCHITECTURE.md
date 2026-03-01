# Enterprise Microservices Architecture

## Overview

This document describes the enterprise-grade microservices architecture for the AI Travel Agent application.

## Architecture Diagram

```
                                  ┌──────────────┐
                                  │   Internet   │
                                  └──────┬───────┘
                                         │
                                         ▼
                          ┌──────────────────────────┐
                          │   AWS Load Balancer      │
                          │   (Port 80)              │
                          └──────────┬───────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────┐
│                    Gateway Service (Port 8000)                  │
│  - Entry point for all client requests                         │
│  - Request routing and aggregation                             │
│  - Analytics event tracking                                     │
└────┬──────────────────────────┬─────────────────────────────────┘
     │                          │
     ▼                          ▼
┌─────────────────┐   ┌──────────────────────┐
│ Booking Service │   │  Analytics Service   │
│  (Port 8001)    │   │   (Port 8005)        │
│                 │   │                      │
│ - Create        │   │ - Event tracking     │
│   itineraries   │   │ - Metrics & reports  │
│ - Generate AI   │   │ - User analytics     │
│   content       │   │                      │
│ - Manage        │   └──────────────────────┘
│   bookings      │
└────┬────────────┘
     │
     │ calls
     ▼
┌─────────────────┐
│ Payment Service │
│  (Port 8002)    │
│                 │
│ - Process       │
│   payments      │
│ - Update status │
│ - Send to queue │
└────┬────────────┘
     │
     │ calls
     ▼
┌─────────────────┐
│  Fraud Service  │
│  (Port 8003)    │
│                 │
│ - Risk analysis │
│ - Fraud         │
│   detection     │
│ - Score calc    │
└─────────────────┘

     │
     │ publishes to
     ▼
┌──────────────────────────────────┐
│      RabbitMQ Message Broker      │
│                                  │
│  Queue: notifications            │
└──────────┬───────────────────────┘
           │
           │ consumes from
           ▼
┌─────────────────────┐
│ Notification Service│
│   (Port 8004)       │
│                     │
│ - Email/SMS/Push    │
│ - Async processing  │
│ - Status tracking   │
└─────────────────────┘

┌────────────────────────┐
│  Client Simulator      │
│                        │
│ - Load testing         │
│ - User journey sim     │
│ - Continuous traffic   │
└────────────────────────┘

┌────────────────────────────────────────┐
│        Supabase Database               │
│                                        │
│  Tables:                               │
│  - users                               │
│  - itineraries                         │
│  - bookings                            │
│  - payments                            │
│  - fraud_checks                        │
│  - notifications                       │
│  - analytics_events                    │
└────────────────────────────────────────┘
```

## Service Details

### 1. Gateway Service (Port 8000)

**Purpose**: API Gateway and entry point for all external requests

**Responsibilities**:
- Route requests to appropriate microservices
- Request/response aggregation
- Analytics event tracking
- Error handling and response formatting

**Endpoints**:
- `POST /api/itineraries` - Create travel itinerary
- `POST /api/bookings` - Create booking and initiate payment
- `GET /api/bookings/{id}` - Get booking details
- `GET /health` - Health check

**Dependencies**:
- Booking Service
- Analytics Service
- Supabase

**Replicas**: 2 (for high availability)

---

### 2. Booking Service (Port 8001)

**Purpose**: Manage itineraries and bookings

**Responsibilities**:
- Generate AI-powered travel itineraries using Groq LLM
- Manage user accounts
- Create and manage bookings
- Coordinate with Payment Service
- Update itinerary status based on payment

**Endpoints**:
- `POST /itineraries` - Create new itinerary
- `POST /bookings` - Create booking and call payment service
- `GET /bookings/{id}` - Get booking details
- `GET /health` - Health check

**Dependencies**:
- Payment Service (HTTP calls)
- Groq LLM API (external)
- Supabase

**Replicas**: 2

---

### 3. Payment Service (Port 8002)

**Purpose**: Process payments and coordinate fraud checks

**Responsibilities**:
- Create payment records
- Coordinate with Fraud Service
- Update payment status
- Publish notification events to message queue
- Handle payment success/failure flows

**Endpoints**:
- `POST /payments` - Process payment
- `GET /payments/{id}` - Get payment details
- `GET /health` - Health check

**Dependencies**:
- Fraud Service (HTTP calls)
- RabbitMQ (message publishing)
- Supabase

**Replicas**: 2

---

### 4. Fraud Service (Port 8003)

**Purpose**: Fraud detection and risk assessment

**Responsibilities**:
- Calculate risk scores based on multiple factors
- Analyze transaction patterns
- Make approve/reject/manual review decisions
- Store fraud check results

**Risk Factors**:
- Transaction amount (high amounts increase risk)
- Payment method (new cards increase risk)
- Transaction velocity (simulated)
- IP location analysis (simulated)

**Endpoints**:
- `POST /fraud-check` - Perform fraud check
- `GET /fraud-checks/{id}` - Get fraud check details
- `GET /health` - Health check

**Dependencies**:
- Supabase

**Replicas**: 2

---

### 5. Notification Service (Port 8004)

**Purpose**: Async notification processing

**Responsibilities**:
- Consume messages from RabbitMQ queue
- Send notifications (email/SMS/push - simulated)
- Track notification status
- Handle different notification types

**Notification Types**:
- Payment success
- Payment failure (fraud)
- Booking confirmation

**Endpoints**:
- `GET /notifications/{user_id}` - Get user notifications
- `GET /health` - Health check

**Dependencies**:
- RabbitMQ (message consumption)
- Supabase

**Replicas**: 2 (for redundancy)

---

### 6. Analytics Service (Port 8005)

**Purpose**: Event tracking and analytics

**Responsibilities**:
- Track events from all services
- Provide analytics summaries
- User behavior analysis
- Service metrics

**Endpoints**:
- `POST /events` - Track analytics event
- `GET /analytics/summary` - Get overall analytics summary
- `GET /analytics/events` - Get filtered events
- `GET /analytics/user/{id}` - Get user-specific analytics
- `GET /health` - Health check

**Dependencies**:
- Supabase

**Replicas**: 2

---

### 7. Client Simulator

**Purpose**: Simulate real user traffic for testing

**Responsibilities**:
- Generate realistic user journeys
- Create itineraries and bookings
- Provide continuous load testing
- Test end-to-end flows

**Configuration**:
- Continuous mode (default)
- Configurable number of users
- Configurable concurrency
- Random cities and interests

**Replicas**: 1

---

## Communication Patterns

### Synchronous (HTTP/REST)
- Gateway → Booking Service
- Gateway → Analytics Service
- Booking → Payment Service
- Payment → Fraud Service

### Asynchronous (Message Queue)
- Payment Service → RabbitMQ → Notification Service

### Database
- All services → Supabase (via Supabase client SDK)

---

## Data Flow Examples

### Creating a Booking

```
1. Client → Gateway Service
   POST /api/bookings
   {itinerary_id, user_id, payment_method}

2. Gateway → Booking Service
   POST /bookings

3. Booking Service → Payment Service
   POST /payments
   {booking_id, amount, payment_method, user_id}

4. Payment Service → Fraud Service
   POST /fraud-check
   {payment_id, amount, payment_method, user_id}

5. Fraud Service → Response
   {fraud_check_id, risk_score, status, reason}

6. Payment Service → RabbitMQ
   Publish to 'notifications' queue
   {type, user_id, booking_id, payment_id}

7. Notification Service ← RabbitMQ
   Consume from 'notifications' queue
   Send notification

8. Gateway → Client
   {booking_id, payment_id, status, fraud_check}
```

---

## Technology Stack

### Services
- **Framework**: FastAPI
- **Language**: Python 3.10
- **ASGI Server**: Uvicorn

### Database
- **Primary DB**: Supabase (PostgreSQL)
- **ORM**: Supabase Python SDK
- **Schema Management**: Migrations

### Message Broker
- **Broker**: RabbitMQ 3.12
- **Client Library**: Pika
- **Queue Pattern**: Work queue

### AI/ML
- **LLM Provider**: Groq
- **Model**: LLaMA 3.3 70B
- **Framework**: LangChain

### Container & Orchestration
- **Containerization**: Docker
- **Orchestration**: Kubernetes (AWS EKS)
- **Registry**: Amazon ECR

### Observability
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana, Filebeat)
- **Log Format**: JSON structured logging
- **Health Checks**: HTTP health endpoints

---

## Database Schema

### users
- id (uuid, pk)
- email (text, unique)
- full_name (text)
- status (text)
- created_at, updated_at (timestamptz)

### itineraries
- id (uuid, pk)
- user_id (uuid, fk)
- city (text)
- interests (text[])
- content (text)
- status (text: draft, booked, cancelled)
- created_at, updated_at (timestamptz)

### bookings
- id (uuid, pk)
- itinerary_id (uuid, fk)
- user_id (uuid, fk)
- status (text: pending, confirmed, cancelled, failed)
- total_amount (decimal)
- payment_id (uuid, fk)
- created_at, updated_at (timestamptz)

### payments
- id (uuid, pk)
- booking_id (uuid, fk)
- amount (decimal)
- currency (text)
- status (text: pending, processing, completed, failed, refunded)
- payment_method (text)
- fraud_check_id (uuid, fk)
- created_at, updated_at (timestamptz)

### fraud_checks
- id (uuid, pk)
- payment_id (uuid, fk)
- risk_score (decimal 0-100)
- status (text: approved, rejected, manual_review)
- reason (text)
- checked_at (timestamptz)
- metadata (jsonb)

### notifications
- id (uuid, pk)
- user_id (uuid, fk)
- type (text: email, sms, push)
- channel (text: booking, payment, general)
- subject (text)
- message (text)
- status (text: pending, sent, failed)
- sent_at, created_at (timestamptz)

### analytics_events
- id (uuid, pk)
- event_type (text)
- service_name (text)
- user_id (uuid, fk)
- metadata (jsonb)
- created_at (timestamptz)

---

## Security

### Authentication & Authorization
- Row Level Security (RLS) enabled on all tables
- Service role key for inter-service communication
- User-specific data access via RLS policies

### Network Security
- Internal services use ClusterIP (not exposed externally)
- Only Gateway Service has LoadBalancer (external access)
- TLS/SSL termination at Load Balancer

### Secrets Management
- Kubernetes Secrets for sensitive data
- Environment variables for configuration
- No hardcoded credentials

---

## Scalability Considerations

### Horizontal Scaling
- All services designed to be stateless
- Can scale replicas independently
- Message queue ensures async processing doesn't block

### Database Scaling
- Supabase handles database scaling
- Connection pooling configured
- Indexes on frequently queried columns

### Message Queue
- RabbitMQ can be clustered for HA
- Durable queues for message persistence
- Dead letter queues for failed messages (future enhancement)

---

## Monitoring & Observability

### Health Checks
- All services expose `/health` endpoint
- Kubernetes liveness probes
- Kubernetes readiness probes

### Logging
- Structured JSON logging
- Service name and metadata in every log
- Collected by Filebeat → Logstash → Elasticsearch
- Viewable in Kibana dashboard

### Metrics (Future Enhancement)
- Prometheus metrics endpoint
- Request rates, latencies, error rates
- Service-specific metrics

---

## Deployment

### Prerequisites
- AWS EKS cluster
- kubectl configured
- Docker installed
- AWS CLI configured
- Supabase project setup

### Deployment Steps
1. Set environment variables (GROQ_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
2. Run `./deploy-microservices.sh`
3. Wait for all services to be ready
4. Access Gateway via LoadBalancer URL

### Verification
```bash
kubectl get pods
kubectl get svc
kubectl logs -l app=gateway-service
```

---

## API Examples

### Create Itinerary
```bash
curl -X POST http://<GATEWAY_URL>/api/itineraries \
  -H "Content-Type: application/json" \
  -d '{
    "city": "Paris",
    "interests": "museums, food, wine",
    "user_email": "user@example.com",
    "user_name": "John Doe"
  }'
```

### Create Booking
```bash
curl -X POST http://<GATEWAY_URL>/api/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "itinerary_id": "uuid-here",
    "user_id": "uuid-here",
    "payment_method": "credit_card"
  }'
```

### Get Booking
```bash
curl http://<GATEWAY_URL>/api/bookings/{booking_id}
```

### Get Analytics Summary
```bash
curl http://<ANALYTICS_SERVICE>:8005/analytics/summary?days=7
```

---

## Future Enhancements

1. Add Prometheus metrics
2. Implement distributed tracing (Jaeger/Zipkin)
3. Add API rate limiting
4. Implement circuit breakers (Resilience4j)
5. Add caching layer (Redis)
6. Implement event sourcing
7. Add GraphQL gateway option
8. Enhance fraud detection with ML models
9. Add real email/SMS providers
10. Implement A/B testing framework

---

## Support

For issues and questions, refer to:
- Service logs in Kibana
- Health check endpoints
- Database query logs in Supabase

