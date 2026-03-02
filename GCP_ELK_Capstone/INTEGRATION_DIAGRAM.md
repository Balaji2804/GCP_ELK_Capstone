# Complete System Integration Diagram

## Full Stack Architecture with Frontend

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER LAYER                                      │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                      User's Web Browser                             │    │
│  │                                                                     │    │
│  │  URL: http://<STREAMLIT_LOADBALANCER>                              │    │
│  │                                                                     │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │    │
│  │  │  Plan        │  │  Book        │  │  My          │            │    │
│  │  │  Itinerary   │  │  Trip        │  │  Bookings    │            │    │
│  │  │  (Tab 1)     │  │  (Tab 2)     │  │  (Tab 3)     │            │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘            │    │
│  │                                                                     │    │
│  │  Sidebar: User Profile (Email: user@example.com)                   │    │
│  └────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │ HTTP Requests
                                       │ (httpx client)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PRESENTATION LAYER                                  │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                 Streamlit Application (app.py)                      │    │
│  │                                                                     │    │
│  │  Service: streamlit-service (LoadBalancer:80 → 8501)               │    │
│  │  Deployment: streamlit-app (1 replica)                              │    │
│  │                                                                     │    │
│  │  Environment:                                                       │    │
│  │    GATEWAY_URL=http://gateway-service:8000                          │    │
│  │                                                                     │    │
│  │  Session State:                                                     │    │
│  │    - user_id                                                        │    │
│  │    - user_email                                                     │    │
│  │    - current_itinerary                                              │    │
│  │    - booking_history[]                                              │    │
│  │                                                                     │    │
│  │  API Calls:                                                         │    │
│  │    - POST /api/itineraries      (Create itinerary)                 │    │
│  │    - POST /api/bookings         (Create booking)                   │    │
│  │    - GET  /api/bookings/{id}    (Get booking details)              │    │
│  └────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │ HTTP POST/GET
                                       │ JSON payload
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API GATEWAY LAYER                                  │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │               Gateway Service (Port 8000)                           │    │
│  │                                                                     │    │
│  │  Service: gateway-service (LoadBalancer:80 → 8000)                 │    │
│  │  Deployment: gateway-service (2 replicas)                           │    │
│  │                                                                     │    │
│  │  Routes:                                                            │    │
│  │    POST /api/itineraries  → http://booking-service:8001            │    │
│  │    POST /api/bookings     → http://booking-service:8001            │    │
│  │    GET  /api/bookings/:id → http://booking-service:8001            │    │
│  │    All requests           → http://analytics-service:8005 (async)  │    │
│  │                                                                     │    │
│  │  Responsibilities:                                                  │    │
│  │    - Request routing                                                │    │
│  │    - Response aggregation                                           │    │
│  │    - Analytics event tracking                                       │    │
│  │    - Error handling                                                 │    │
│  └────────────────────────────────────────────────────────────────────┘    │
└──────────────────────┬───────────────────────┬───────────────────────────────┘
                       │                       │
                       ▼                       ▼
        ┌──────────────────────┐   ┌──────────────────────┐
        │  Booking Service     │   │  Analytics Service   │
        │  (Port 8001)         │   │  (Port 8005)         │
        └──────────┬───────────┘   └──────────────────────┘
                   │                          │
                   ▼                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        BUSINESS LOGIC LAYER                                  │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │               Booking Service (Port 8001)                           │    │
│  │                                                                     │    │
│  │  Service: booking-service (ClusterIP:8001)                          │    │
│  │  Deployment: booking-service (2 replicas)                           │    │
│  │                                                                     │    │
│  │  Endpoints:                                                         │    │
│  │    POST /itineraries  → Create user & itinerary                    │    │
│  │                       → Call Groq LLM API                           │    │
│  │                       → Save to Supabase                            │    │
│  │    POST /bookings     → Create booking                              │    │
│  │                       → Call Payment Service                        │    │
│  │                       → Update booking status                       │    │
│  │    GET  /bookings/:id → Retrieve booking with joins                │    │
│  │                                                                     │    │
│  │  External Dependencies:                                             │    │
│  │    - Groq LLM API (llama-3.3-70b-versatile)                        │    │
│  │    - Payment Service (http://payment-service:8002)                  │    │
│  └────────────────────────────────────┬───────────────────────────────┘    │
│                                       │                                      │
│                                       ▼                                      │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │               Payment Service (Port 8002)                           │    │
│  │                                                                     │    │
│  │  Service: payment-service (ClusterIP:8002)                          │    │
│  │  Deployment: payment-service (2 replicas)                           │    │
│  │                                                                     │    │
│  │  Endpoints:                                                         │    │
│  │    POST /payments → Create payment record                          │    │
│  │                   → Call Fraud Service                              │    │
│  │                   → Update payment status                           │    │
│  │                   → Publish to RabbitMQ                             │    │
│  │                                                                     │    │
│  │  Dependencies:                                                      │    │
│  │    - Fraud Service (http://fraud-service:8003)                     │    │
│  │    - RabbitMQ (rabbitmq:5672)                                      │    │
│  └────────────────────────────────────┬───────────────────────────────┘    │
│                                       │                                      │
│                                       ▼                                      │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │               Fraud Service (Port 8003)                             │    │
│  │                                                                     │    │
│  │  Service: fraud-service (ClusterIP:8003)                            │    │
│  │  Deployment: fraud-service (2 replicas)                             │    │
│  │                                                                     │    │
│  │  Endpoints:                                                         │    │
│  │    POST /fraud-check → Calculate risk score                        │    │
│  │                      → Analyze transaction                          │    │
│  │                      → Return: approved/rejected/manual_review      │    │
│  │                                                                     │    │
│  │  Risk Factors:                                                      │    │
│  │    - Transaction amount                                             │    │
│  │    - Payment method                                                 │    │
│  │    - Transaction velocity (simulated)                               │    │
│  │    - IP location (simulated)                                        │    │
│  └────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                      MESSAGING & ASYNC LAYER                                 │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                    RabbitMQ Message Broker                          │    │
│  │                                                                     │    │
│  │  Service: rabbitmq (ClusterIP:5672, 15672)                          │    │
│  │  Deployment: rabbitmq (1 replica)                                   │    │
│  │                                                                     │    │
│  │  Queues:                                                            │    │
│  │    - notifications (durable)                                        │    │
│  │                                                                     │    │
│  │  Message Flow:                                                      │    │
│  │    Payment Service → Publish → RabbitMQ → Consume → Notification   │    │
│  │                                                                     │    │
│  │  Message Format:                                                    │    │
│  │    {                                                                │    │
│  │      "type": "payment_success" | "payment_failed_fraud",           │    │
│  │      "user_id": "uuid",                                            │    │
│  │      "booking_id": "uuid",                                         │    │
│  │      "payment_id": "uuid",                                         │    │
│  │      "amount": "299.99",                                           │    │
│  │      "reason": "optional"                                          │    │
│  │    }                                                                │    │
│  └────────────────────────────────────┬───────────────────────────────┘    │
│                                       │                                      │
│                                       ▼ Consume                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │             Notification Service (Port 8004)                        │    │
│  │                                                                     │    │
│  │  Service: notification-service (ClusterIP:8004)                     │    │
│  │  Deployment: notification-service (2 replicas)                      │    │
│  │                                                                     │    │
│  │  Background Worker:                                                 │    │
│  │    - Consumes from "notifications" queue                            │    │
│  │    - Generates email/SMS/push (simulated)                           │    │
│  │    - Saves notification to Supabase                                 │    │
│  │                                                                     │    │
│  │  Endpoints:                                                         │    │
│  │    GET /notifications/:user_id → Get user notifications            │    │
│  └────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA PERSISTENCE LAYER                               │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                     Supabase Database                               │    │
│  │                     (PostgreSQL)                                    │    │
│  │                                                                     │    │
│  │  URL: https://<project>.supabase.co                                │    │
│  │  Authentication: Service Role Key                                   │    │
│  │                                                                     │    │
│  │  Tables:                                                            │    │
│  │    1. users (id, email, full_name, status, created_at)             │    │
│  │    2. itineraries (id, user_id, city, interests[], content)        │    │
│  │    3. bookings (id, itinerary_id, user_id, status, amount)         │    │
│  │    4. payments (id, booking_id, amount, status, method)            │    │
│  │    5. fraud_checks (id, payment_id, risk_score, status)            │    │
│  │    6. notifications (id, user_id, type, message, status)           │    │
│  │    7. analytics_events (id, event_type, service_name, metadata)    │    │
│  │                                                                     │    │
│  │  Security:                                                          │    │
│  │    - Row Level Security (RLS) enabled on all tables                │    │
│  │    - Service role bypasses RLS for backend operations              │    │
│  │    - User-specific policies for user access                        │    │
│  └────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         OBSERVABILITY LAYER                                  │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                         ELK Stack                                   │    │
│  │                      (Namespace: logging)                           │    │
│  │                                                                     │    │
│  │  ┌──────────────────────────────────────────────────────────────┐ │    │
│  │  │  Filebeat DaemonSet (runs on every node)                     │ │    │
│  │  │    - Monitors /var/log/containers/*.log                      │ │    │
│  │  │    - Collects logs from all pods                             │ │    │
│  │  │    - Adds Kubernetes metadata                                │ │    │
│  │  │    - Sends to Logstash:5044                                  │ │    │
│  │  └────────────────────┬─────────────────────────────────────────┘ │    │
│  │                       ▼                                             │    │
│  │  ┌──────────────────────────────────────────────────────────────┐ │    │
│  │  │  Logstash (Port 5044)                                        │ │    │
│  │  │    - Receives logs from Filebeat                            │ │    │
│  │  │    - Processes and filters logs                              │ │    │
│  │  │    - Sends to Elasticsearch:9200                             │ │    │
│  │  └────────────────────┬─────────────────────────────────────────┘ │    │
│  │                       ▼                                             │    │
│  │  ┌──────────────────────────────────────────────────────────────┐ │    │
│  │  │  Elasticsearch (Port 9200)                                   │ │    │
│  │  │    - Stores logs in indices (filebeat-YYYY.MM.DD)            │ │    │
│  │  │    - Provides search API                                     │ │    │
│  │  │    - 2GB persistent storage (EBS)                            │ │    │
│  │  └────────────────────┬─────────────────────────────────────────┘ │    │
│  │                       ▼                                             │    │
│  │  ┌──────────────────────────────────────────────────────────────┐ │    │
│  │  │  Kibana (Port 5601 → NodePort 30601)                         │ │    │
│  │  │    - Web UI for viewing logs                                 │ │    │
│  │  │    - Create index pattern: filebeat-*                        │ │    │
│  │  │    - Filter by service, pod, container                       │ │    │
│  │  │    - Access: http://<NODE_IP>:30601                          │ │    │
│  │  └──────────────────────────────────────────────────────────────┘ │    │
│  └────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         TESTING & SIMULATION LAYER                           │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │               Client Simulator (Continuous)                         │    │
│  │                                                                     │    │
│  │  Deployment: client-simulator (1 replica)                           │    │
│  │                                                                     │    │
│  │  Behavior:                                                          │    │
│  │    - Generates random users                                         │    │
│  │    - Creates itineraries via Gateway API                            │    │
│  │    - Creates bookings with random payment methods                   │    │
│  │    - Runs continuously with delays                                  │    │
│  │                                                                     │    │
│  │  Configuration:                                                     │    │
│  │    GATEWAY_URL=http://gateway-service:8000                          │    │
│  │    SIMULATION_MODE=continuous                                       │    │
│  │                                                                     │    │
│  │  Cities: Paris, Tokyo, New York, London, Dubai...                  │    │
│  │  Interests: museums, food, beaches, shopping...                    │    │
│  │  Payment Methods: credit_card, debit_card, paypal, new_card        │    │
│  └────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                      KUBERNETES INFRASTRUCTURE                               │
│                                                                              │
│  Cluster: ai-travel-agent (AWS EKS, ap-south-1)                             │
│  Nodes: 2x t3.medium (2 vCPU, 4GB RAM each)                                 │
│                                                                              │
│  Namespaces:                                                                 │
│    - default (microservices + streamlit)                                     │
│    - logging (ELK stack)                                                     │
│                                                                              │
│  Deployments: 14 total                                                       │
│    - streamlit-app (1)                                                       │
│    - gateway-service (2)                                                     │
│    - booking-service (2)                                                     │
│    - payment-service (2)                                                     │
│    - fraud-service (2)                                                       │
│    - notification-service (2)                                                │
│    - analytics-service (2)                                                   │
│    - client-simulator (1)                                                    │
│    - rabbitmq (1)                                                            │
│    - elasticsearch (1)                                                       │
│    - logstash (1)                                                            │
│    - kibana (1)                                                              │
│                                                                              │
│  DaemonSets: 1 (filebeat)                                                    │
│                                                                              │
│  Services: 14 total                                                          │
│    External: streamlit-service, gateway-service, kibana                      │
│    Internal: booking, payment, fraud, notification, analytics, rabbitmq,     │
│              elasticsearch, logstash                                         │
│                                                                              │
│  Secrets: 2                                                                  │
│    - microservices-secrets (GROQ_API_KEY, SUPABASE_URL, SUPABASE_KEY)       │
│    - llmops-secrets (GROQ_API_KEY - legacy)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: User Creates Booking

```
1. USER OPENS APP
   Browser → http://<STREAMLIT_LB>
   Streamlit UI loads with 3 tabs + sidebar

2. USER LOGS IN
   Sidebar Form → Email: user@example.com, Name: John Doe
   st.session_state.user_email = "user@example.com"
   st.session_state.user_name = "John Doe"

3. USER CREATES ITINERARY (Tab 1)
   Input: City="Paris", Interests="museums, food, wine"
   Click: "Generate Itinerary"

   Streamlit → Gateway Service
     POST /api/itineraries
     {
       "city": "Paris",
       "interests": "museums, food, wine",
       "user_email": "user@example.com",
       "user_name": "John Doe"
     }

   Gateway → Booking Service
     POST /itineraries

   Booking Service:
     - Check if user exists (SELECT * FROM users WHERE email = ...)
     - Create user if not exists (INSERT INTO users ...)
     - Call Groq LLM API with city + interests
     - Create itinerary (INSERT INTO itineraries ...)
     - Return: {itinerary_id, user_id, city, content, status: "draft"}

   Gateway → Analytics Service
     POST /events {event_type: "itinerary_created", user_id: ...}

   Gateway → Streamlit
     Response: {itinerary_id, user_id, city, content, status}

   Streamlit:
     st.session_state.current_itinerary = result
     st.session_state.user_id = result['user_id']
     Display itinerary with metrics
     Show "Ready to book? Go to Book Trip tab"

4. USER BOOKS TRIP (Tab 2)
   View: Itinerary preview, Pricing: $299.99
   Select: Payment Method = "credit_card"
   Check: "I agree to terms and conditions"
   Click: "Complete Booking"

   Streamlit → Gateway Service
     POST /api/bookings
     {
       "itinerary_id": "<uuid>",
       "user_id": "<uuid>",
       "payment_method": "credit_card"
     }

   Gateway → Booking Service
     POST /bookings

   Booking Service:
     - Create booking (INSERT INTO bookings ... status='pending')

     Booking → Payment Service
       POST /payments
       {
         "booking_id": "<uuid>",
         "amount": "299.99",
         "payment_method": "credit_card",
         "user_id": "<uuid>"
       }

     Payment Service:
       - Create payment (INSERT INTO payments ... status='processing')

       Payment → Fraud Service
         POST /fraud-check
         {
           "payment_id": "<uuid>",
           "amount": "299.99",
           "payment_method": "credit_card",
           "user_id": "<uuid>"
         }

       Fraud Service:
         - Calculate risk score (amount + method + velocity + IP)
         - Risk Score: 25.5 (Low)
         - Status: "approved"
         - Reason: "No risk factors detected"
         - INSERT INTO fraud_checks ...
         - Return: {fraud_check_id, risk_score: 25.5, status: "approved"}

       Payment Service:
         - Update payment status to "completed"
         - Publish to RabbitMQ:
           Queue: "notifications"
           Message: {
             "type": "payment_success",
             "user_id": "<uuid>",
             "booking_id": "<uuid>",
             "payment_id": "<uuid>",
             "amount": "299.99"
           }
         - Return to Booking Service: {payment_id, status: "confirmed"}

     Booking Service:
       - Update booking status to "confirmed"
       - Update itinerary status to "booked"
       - Return: {booking_id, payment_id, status: "confirmed", fraud_check: {...}}

   Gateway → Analytics Service
     POST /events {event_type: "booking_created", user_id: ...}

   Gateway → Streamlit
     Response: {booking_id, payment_id, status: "confirmed", fraud_check: {...}}

   Streamlit:
     st.session_state.booking_history.append(result)
     st.session_state.current_itinerary = None
     st.success("Booking confirmed successfully!")
     st.balloons()
     Display:
       - Booking ID: <uuid>
       - Payment ID: <uuid>
       - Status: CONFIRMED
       - Risk Score: 25.5/100 (Low risk)
       - Security Status: APPROVED
       - Reason: "No risk factors detected"

5. NOTIFICATION (ASYNC)
   RabbitMQ → Notification Service (Background Consumer)
     Consume from "notifications" queue

     Notification Service:
       - Generate email message
       - INSERT INTO notifications ...
       - Send email (simulated)
       - Update notification status to "sent"

6. USER VIEWS BOOKINGS (Tab 3)
   Display: Booking history from st.session_state.booking_history
   User clicks: "View Full Details"

   Streamlit → Gateway Service
     GET /api/bookings/<booking_id>

   Gateway → Booking Service
     GET /bookings/<booking_id>

   Booking Service:
     SELECT * FROM bookings
     JOIN itineraries ON itineraries.id = bookings.itinerary_id
     JOIN payments ON payments.id = bookings.payment_id
     WHERE bookings.id = '<booking_id>'

     Return: Complete booking object with joins

   Gateway → Streamlit
     Response: {booking details with itinerary and payment}

   Streamlit:
     st.json(result)  # Display full JSON data
```

---

## Complete Technology Stack Map

```
Layer               Technology          Version     Purpose
──────────────────────────────────────────────────────────────────
Frontend            Streamlit           Latest      Web UI
                    httpx               0.26.0      HTTP client

API Gateway         FastAPI             0.109       REST framework
                    Uvicorn             0.27        ASGI server

Microservices       FastAPI             0.109       REST framework
                    Python              3.10        Language

AI/LLM              Groq Cloud          API         LLM provider
                    LLaMA 3.3 70B       Model       AI model
                    LangChain           0.1.0       LLM framework

Message Queue       RabbitMQ            3.12        AMQP broker
                    Pika                1.3.2       Python client

Database            Supabase            Cloud       PostgreSQL
                    Supabase SDK        2.3.0       Python client

Logging             Elasticsearch       7.17        Log storage
                    Logstash            7.17        Log processing
                    Kibana              7.17        Log visualization
                    Filebeat            7.17        Log collection

Containers          Docker              Latest      Containerization
                    Amazon ECR          N/A         Image registry

Orchestration       Kubernetes          1.28        Container orchestration
                    AWS EKS             N/A         Managed K8s

Cloud               AWS                 N/A         Cloud provider
                    EC2 (t3.medium)     N/A         Compute
                    EBS (gp2)           N/A         Storage
                    ELB                 N/A         Load balancer
```

---

This diagram shows the complete integration of frontend, backend, and infrastructure layers.

