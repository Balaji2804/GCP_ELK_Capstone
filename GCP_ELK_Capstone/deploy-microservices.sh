#!/bin/bash

set -e

echo "=========================================="
echo "Enterprise Travel Agent - Microservices Deployment"
echo "=========================================="

CLUSTER_NAME="ai-travel-agent"
AWS_REGION=${AWS_REGION:-"ap-south-1"}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

if [ -z "$GROQ_API_KEY" ]; then
    print_error "GROQ_API_KEY environment variable not set"
    read -p "Enter your GROQ API Key: " GROQ_API_KEY
fi

if [ -z "$SUPABASE_URL" ]; then
    print_error "SUPABASE_URL environment variable not set"
    read -p "Enter your Supabase URL: " SUPABASE_URL
fi

if [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    print_error "SUPABASE_SERVICE_ROLE_KEY environment variable not set"
    read -p "Enter your Supabase Service Role Key: " SUPABASE_SERVICE_ROLE_KEY
fi

print_info "Creating ECR repositories..."
services=("gateway-service" "booking-service" "payment-service" "fraud-service" "notification-service" "analytics-service" "client-simulator")

for service in "${services[@]}"; do
    if aws ecr describe-repositories --repository-names $service --region $AWS_REGION &> /dev/null; then
        print_warning "ECR repository '$service' already exists"
    else
        aws ecr create-repository --repository-name $service --region $AWS_REGION
        print_info "Created ECR repository: $service"
    fi
done

print_info "Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

print_info "Building and pushing Docker images..."
cd /tmp/cc-agent/64225349/project/GCP_ELK_Capstone

for service in "${services[@]}"; do
    print_info "Building $service..."
    docker build -f services/${service/-//}/Dockerfile -t $service:latest .
    docker tag $service:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$service:latest
    docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$service:latest
    print_info "Pushed $service to ECR"
done

print_info "Updating Kubernetes manifests with ECR URLs..."
for file in k8s/*.yaml; do
    sed -i.bak "s|<AWS_ACCOUNT_ID>|$AWS_ACCOUNT_ID|g" "$file"
    sed -i.bak "s|<REGION>|$AWS_REGION|g" "$file"
done

print_info "Creating Kubernetes secrets..."
kubectl create secret generic microservices-secrets \
    --from-literal=GROQ_API_KEY=$GROQ_API_KEY \
    --from-literal=SUPABASE_URL=$SUPABASE_URL \
    --from-literal=SUPABASE_SERVICE_ROLE_KEY=$SUPABASE_SERVICE_ROLE_KEY \
    --dry-run=client -o yaml | kubectl apply -f -

print_info "Deploying RabbitMQ..."
kubectl apply -f k8s/rabbitmq.yaml

print_info "Waiting for RabbitMQ to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/rabbitmq

print_info "Deploying microservices..."
kubectl apply -f k8s/fraud-service.yaml
kubectl apply -f k8s/payment-service.yaml
kubectl apply -f k8s/booking-service.yaml
kubectl apply -f k8s/notification-service.yaml
kubectl apply -f k8s/analytics-service.yaml
kubectl apply -f k8s/gateway-service.yaml

print_info "Waiting for services to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/fraud-service
kubectl wait --for=condition=available --timeout=300s deployment/payment-service
kubectl wait --for=condition=available --timeout=300s deployment/booking-service
kubectl wait --for=condition=available --timeout=300s deployment/notification-service
kubectl wait --for=condition=available --timeout=300s deployment/analytics-service
kubectl wait --for=condition=available --timeout=300s deployment/gateway-service

print_info "Deploying client simulator..."
kubectl apply -f k8s/client-simulator.yaml

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""

print_info "Getting service URLs..."
echo ""

GATEWAY_LB=$(kubectl get svc gateway-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "Pending...")
if [ "$GATEWAY_LB" == "Pending..." ]; then
    print_warning "Gateway LoadBalancer is still provisioning. Run this command to check status:"
    echo "kubectl get svc gateway-service"
else
    echo "Gateway API URL: http://$GATEWAY_LB"
fi

echo ""
print_info "Check all pods:"
echo "kubectl get pods"
echo ""
print_info "Check all services:"
echo "kubectl get svc"
echo ""
print_info "View logs from a service:"
echo "kubectl logs -l app=gateway-service --tail=100"
echo ""
echo "=========================================="
