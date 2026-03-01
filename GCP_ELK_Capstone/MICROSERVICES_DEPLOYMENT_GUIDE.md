# Enterprise Microservices Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Detailed Deployment Steps](#detailed-deployment-steps)
4. [Verification](#verification)
5. [Testing the System](#testing-the-system)
6. [Troubleshooting](#troubleshooting)
7. [Monitoring](#monitoring)

---

## Prerequisites

### Required Tools
- AWS CLI (configured with credentials)
- kubectl (v1.28+)
- eksctl (for EKS cluster management)
- Docker (for building images)
- curl/httpie (for API testing)

### Required Accounts & Keys
- AWS account with admin access
- Supabase project (free tier works)
- Groq API key (free tier available)

### EKS Cluster
You should already have an EKS cluster running from the previous deployment. If not:

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

```bash
export GROQ_API_KEY="your_groq_api_key"
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="your_service_role_key"

chmod +x deploy-microservices.sh
./deploy-microservices.sh
```

Wait for deployment to complete, then access the Gateway API via the LoadBalancer URL.

---

## Detailed Deployment Steps

### Step 1: Verify EKS Cluster

```bash
kubectl get nodes

kubectl config current-context

eksctl get cluster --name ai-travel-agent --region ap-south-1
```

You should see 2 nodes in Ready state.

---

### Step 2: Set Environment Variables

```bash
export GROQ_API_KEY="gsk_xxxxxxxxxxxxx"
export SUPABASE_URL="https://xxxxxxxxxxxxx.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
export AWS_REGION="ap-south-1"
```

To get your Supabase credentials:
1. Go to https://supabase.com/dashboard
2. Select your project
3. Go to Settings → API
4. Copy "URL" and "service_role secret"

To get your Groq API key:
1. Go to https://console.groq.com
2. Navigate to API Keys
3. Create a new API key

---

### Step 3: Database Migration

The database schema has already been applied to your Supabase instance. Verify:

```bash
curl -X GET "$SUPABASE_URL/rest/v1/users?select=*" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY"
```

Should return an empty array or existing users.

---

### Step 4: Create ECR Repositories

```bash
services=("gateway-service" "booking-service" "payment-service" "fraud-service" "notification-service" "analytics-service" "client-simulator")

for service in "${services[@]}"; do
    aws ecr create-repository \
      --repository-name $service \
      --region $AWS_REGION \
      --image-scanning-configuration scanOnPush=true || true
done
```

---

### Step 5: Build and Push Docker Images

```bash
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

cd /tmp/cc-agent/64225349/project/GCP_ELK_Capstone

for service in "${services[@]}"; do
    echo "Building $service..."
    service_dir=${service/-//}

    docker build \
      -f services/$service_dir/Dockerfile \
      -t $service:latest \
      .

    docker tag $service:latest \
      $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$service:latest

    docker push \
      $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$service:latest

    echo "Pushed $service"
done
```

This will take 10-15 minutes depending on your internet speed.

---

### Step 6: Update Kubernetes Manifests

```bash
cd k8s

for file in *.yaml; do
    sed -i.bak "s|<AWS_ACCOUNT_ID>|$AWS_ACCOUNT_ID|g" "$file"
    sed -i.bak "s|<REGION>|$AWS_REGION|g" "$file"
done
```

---

### Step 7: Create Kubernetes Secrets

```bash
kubectl create secret generic microservices-secrets \
    --from-literal=GROQ_API_KEY=$GROQ_API_KEY \
    --from-literal=SUPABASE_URL=$SUPABASE_URL \
    --from-literal=SUPABASE_SERVICE_ROLE_KEY=$SUPABASE_SERVICE_ROLE_KEY \
    --dry-run=client -o yaml | kubectl apply -f -
```

Verify:
```bash
kubectl get secrets microservices-secrets
```

---

### Step 8: Deploy RabbitMQ

```bash
kubectl apply -f k8s/rabbitmq.yaml

kubectl wait --for=condition=available --timeout=300s deployment/rabbitmq

kubectl get pods -l app=rabbitmq
```

---

### Step 9: Deploy Services (in dependency order)

```bash
kubectl apply -f k8s/fraud-service.yaml
kubectl wait --for=condition=available --timeout=300s deployment/fraud-service

kubectl apply -f k8s/payment-service.yaml
kubectl wait --for=condition=available --timeout=300s deployment/payment-service

kubectl apply -f k8s/booking-service.yaml
kubectl wait --for=condition=available --timeout=300s deployment/booking-service

kubectl apply -f k8s/notification-service.yaml
kubectl wait --for=condition=available --timeout=300s deployment/notification-service

kubectl apply -f k8s/analytics-service.yaml
kubectl wait --for=condition=available --timeout=300s deployment/analytics-service

kubectl apply -f k8s/gateway-service.yaml
kubectl wait --for=condition=available --timeout=300s deployment/gateway-service
```

---

### Step 10: Deploy Client Simulator

```bash
kubectl apply -f k8s/client-simulator.yaml
```

---

## Verification

### Check All Pods

```bash
kubectl get pods

NAME                                    READY   STATUS    RESTARTS   AGE
analytics-service-xxxxxxxxx-xxxxx       1/1     Running   0          5m
booking-service-xxxxxxxxx-xxxxx         1/1     Running   0          5m
client-simulator-xxxxxxxxx-xxxxx        1/1     Running   0          2m
fraud-service-xxxxxxxxx-xxxxx           1/1     Running   0          6m
gateway-service-xxxxxxxxx-xxxxx         1/1     Running   0          4m
notification-service-xxxxxxxxx-xxxxx    1/1     Running   0          5m
payment-service-xxxxxxxxx-xxxxx         1/1     Running   0          6m
rabbitmq-xxxxxxxxx-xxxxx                1/1     Running   0          8m
```

All pods should be in Running state with 1/1 Ready.

---

### Check Services

```bash
kubectl get svc

NAME                   TYPE           CLUSTER-IP       EXTERNAL-IP                                                              PORT(S)
analytics-service      ClusterIP      10.100.xxx.xxx   <none>                                                                   8005/TCP
booking-service        ClusterIP      10.100.xxx.xxx   <none>                                                                   8001/TCP
fraud-service          ClusterIP      10.100.xxx.xxx   <none>                                                                   8003/TCP
gateway-service        LoadBalancer   10.100.xxx.xxx   xxxxx.elb.amazonaws.com                                                  80:xxxxx/TCP
notification-service   ClusterIP      10.100.xxx.xxx   <none>                                                                   8004/TCP
payment-service        ClusterIP      10.100.xxx.xxx   <none>                                                                   8002/TCP
rabbitmq               ClusterIP      10.100.xxx.xxx   <none>                                                                   5672/TCP,15672/TCP
```

Gateway service should have an EXTERNAL-IP (LoadBalancer DNS).

---

### Get Gateway URL

```bash
GATEWAY_URL=$(kubectl get svc gateway-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "Gateway URL: http://$GATEWAY_URL"
```

---

### Test Health Checks

```bash
kubectl get pods -l app=gateway-service -o name | head -1 | xargs kubectl exec -it -- curl localhost:8000/health
kubectl get pods -l app=booking-service -o name | head -1 | xargs kubectl exec -it -- curl localhost:8001/health
kubectl get pods -l app=payment-service -o name | head -1 | xargs kubectl exec -it -- curl localhost:8002/health
kubectl get pods -l app=fraud-service -o name | head -1 | xargs kubectl exec -it -- curl localhost:8003/health
kubectl get pods -l app=notification-service -o name | head -1 | xargs kubectl exec -it -- curl localhost:8004/health
kubectl get pods -l app=analytics-service -o name | head -1 | xargs kubectl exec -it -- curl localhost:8005/health
```

Each should return `{"status":"healthy","service":"<service-name>"}`.

---

## Testing the System

### Test 1: Create Itinerary

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

Expected response:
```json
{
  "itinerary_id": "uuid-here",
  "user_id": "uuid-here",
  "city": "Paris",
  "content": "AI-generated itinerary...",
  "status": "draft"
}
```

---

### Test 2: Create Booking

Save the itinerary_id and user_id from above, then:

```bash
curl -X POST http://$GATEWAY_URL/api/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "itinerary_id": "your-itinerary-id",
    "user_id": "your-user-id",
    "payment_method": "credit_card"
  }'
```

Expected response:
```json
{
  "booking_id": "uuid-here",
  "payment_id": "uuid-here",
  "status": "confirmed",
  "fraud_check": {
    "fraud_check_id": "uuid-here",
    "risk_score": 25.5,
    "status": "approved",
    "reason": "No risk factors detected"
  }
}
```

---

### Test 3: Get Booking Details

```bash
curl http://$GATEWAY_URL/api/bookings/{booking_id}
```

---

### Test 4: Check Analytics

```bash
curl http://$GATEWAY_URL/api/analytics/summary?days=7
```

Wait a few minutes for events to accumulate, then:

```bash
kubectl get pods -l app=analytics-service -o name | head -1 | \
  xargs kubectl exec -it -- curl localhost:8005/analytics/summary?days=1
```

---

### Test 5: Check Notifications

Get user_id from earlier tests:

```bash
kubectl get pods -l app=notification-service -o name | head -1 | \
  xargs kubectl exec -it -- curl localhost:8004/notifications/{user_id}
```

---

### Test 6: View Client Simulator Logs

```bash
kubectl logs -l app=client-simulator --tail=50 -f
```

You should see continuous user journey simulations.

---

## Monitoring

### View Service Logs

```bash
kubectl logs -l app=gateway-service --tail=100
kubectl logs -l app=booking-service --tail=100
kubectl logs -l app=payment-service --tail=100
kubectl logs -l app=fraud-service --tail=100
kubectl logs -l app=notification-service --tail=100
kubectl logs -l app=analytics-service --tail=100
```

---

### View ELK Logs (if ELK stack is still deployed)

Access Kibana:
```bash
kubectl get nodes -o wide
```

Open: http://<NODE_IP>:30601

Filter for specific services:
```
kubernetes.labels.app: "gateway-service"
```

---

### Check Database

Login to Supabase dashboard and run:

```sql
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM itineraries;
SELECT COUNT(*) FROM bookings;
SELECT COUNT(*) FROM payments;
SELECT COUNT(*) FROM fraud_checks;
SELECT COUNT(*) FROM notifications;
SELECT COUNT(*) FROM analytics_events;
```

---

### Check RabbitMQ

Port forward to RabbitMQ management UI:

```bash
kubectl port-forward svc/rabbitmq 15672:15672
```

Open: http://localhost:15672
Login: guest/guest

Check queues and message rates.

---

## Troubleshooting

### Issue: Pods Not Starting

```bash
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

Common causes:
- Image pull errors (check ECR permissions)
- Missing secrets
- Resource limits too low
- Dependency service not ready

---

### Issue: Service Communication Errors

Check service DNS resolution:

```bash
kubectl exec -it <pod-name> -- nslookup booking-service
```

Check connectivity:

```bash
kubectl exec -it <pod-name> -- curl http://booking-service:8001/health
```

---

### Issue: Database Connection Errors

Verify secrets:

```bash
kubectl get secret microservices-secrets -o json | jq '.data | map_values(@base64d)'
```

Test connection:

```bash
kubectl exec -it <pod-name> -- python -c "
from supabase import create_client
import os
client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
print(client.table('users').select('*').limit(1).execute())
"
```

---

### Issue: RabbitMQ Connection Errors

Check RabbitMQ is running:

```bash
kubectl get pods -l app=rabbitmq
kubectl logs -l app=rabbitmq
```

Check notification service can connect:

```bash
kubectl logs -l app=notification-service | grep -i rabbitmq
```

---

### Issue: Payment Always Fails

Check fraud service:

```bash
kubectl logs -l app=fraud-service --tail=50
```

The fraud service uses random risk scoring. Try multiple times or check the risk_score in the response.

---

## Scaling

### Scale a Service

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

## Cleanup

### Delete All Microservices

```bash
kubectl delete -f k8s/client-simulator.yaml
kubectl delete -f k8s/gateway-service.yaml
kubectl delete -f k8s/analytics-service.yaml
kubectl delete -f k8s/notification-service.yaml
kubectl delete -f k8s/booking-service.yaml
kubectl delete -f k8s/payment-service.yaml
kubectl delete -f k8s/fraud-service.yaml
kubectl delete -f k8s/rabbitmq.yaml
kubectl delete secret microservices-secrets
```

### Delete ECR Repositories

```bash
services=("gateway-service" "booking-service" "payment-service" "fraud-service" "notification-service" "analytics-service" "client-simulator")

for service in "${services[@]}"; do
    aws ecr delete-repository \
      --repository-name $service \
      --region $AWS_REGION \
      --force
done
```

### Keep ELK Stack (if desired)

The original ELK stack deployment can remain running to collect logs from microservices.

---

## Summary

You now have a fully functioning enterprise-grade microservices architecture with:

- 7 microservices running on EKS
- API Gateway for external access
- Synchronous and asynchronous communication patterns
- Fraud detection in the payment flow
- Analytics tracking
- Automated load testing with client simulator
- Comprehensive logging with ELK
- Database persistence with Supabase
- Message queue for async operations

All services are production-ready with health checks, proper error handling, and scalability built in.
