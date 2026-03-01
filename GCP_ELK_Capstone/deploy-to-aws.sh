#!/bin/bash

# AI Travel Agent - AWS EKS Deployment Script
# Run this script on your EC2 instance after installing all prerequisites

set -e

echo "=========================================="
echo "AI Travel Agent - AWS EKS Deployment"
echo "=========================================="

# Configuration
CLUSTER_NAME="ai-travel-agent"
AWS_REGION="us-east-1"
NODE_TYPE="t3.medium"
NODES=2

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if AWS CLI is configured
print_info "Checking AWS CLI configuration..."
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS CLI not configured. Run 'aws configure' first."
    exit 1
fi

export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
print_info "AWS Account ID: $AWS_ACCOUNT_ID"

# Ask for GROQ API Key
read -p "Enter your GROQ API Key: " GROQ_API_KEY
if [ -z "$GROQ_API_KEY" ]; then
    print_error "GROQ API Key is required!"
    exit 1
fi

# Step 1: Create EKS Cluster
print_info "Creating EKS cluster (this takes 15-20 minutes)..."
if eksctl get cluster --name $CLUSTER_NAME --region $AWS_REGION &> /dev/null; then
    print_warning "Cluster $CLUSTER_NAME already exists. Skipping creation."
else
    eksctl create cluster \
        --name $CLUSTER_NAME \
        --region $AWS_REGION \
        --node-type $NODE_TYPE \
        --nodes $NODES \
        --nodes-min $NODES \
        --nodes-max 4 \
        --managed
fi

# Verify cluster
print_info "Verifying cluster..."
kubectl get nodes

# Step 2: Create logging namespace
print_info "Creating logging namespace..."
kubectl create namespace logging --dry-run=client -o yaml | kubectl apply -f -

# Step 3: Create ECR repository
print_info "Creating ECR repository..."
if aws ecr describe-repositories --repository-names streamlit-app --region $AWS_REGION &> /dev/null; then
    print_warning "ECR repository 'streamlit-app' already exists."
else
    aws ecr create-repository \
        --repository-name streamlit-app \
        --region $AWS_REGION
fi

# Step 4: Build and push Docker image
print_info "Authenticating to ECR..."
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

print_info "Building Docker image..."
docker build -t streamlit-app:latest .

print_info "Tagging Docker image..."
docker tag streamlit-app:latest \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/streamlit-app:latest

print_info "Pushing Docker image to ECR..."
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/streamlit-app:latest

# Step 5: Update k8s-deployment.yaml with ECR image URL
print_info "Updating k8s-deployment.yaml with ECR image URL..."
sed -i.bak "s|<AWS_ACCOUNT_ID>|$AWS_ACCOUNT_ID|g" k8s-deployment.yaml
sed -i.bak "s|<REGION>|$AWS_REGION|g" k8s-deployment.yaml

# Step 6: Create Kubernetes secrets
print_info "Creating Kubernetes secrets..."
kubectl create secret generic llmops-secrets \
    --from-literal=GROQ_API_KEY=$GROQ_API_KEY \
    --dry-run=client -o yaml | kubectl apply -f -

# Step 7: Deploy ELK Stack
print_info "Deploying Elasticsearch..."
kubectl apply -f elasticsearch.yaml

print_info "Waiting for Elasticsearch to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/elasticsearch -n logging

print_info "Deploying Logstash..."
kubectl apply -f logstash.yaml

print_info "Deploying Filebeat..."
kubectl apply -f filebeat.yaml

print_info "Deploying Kibana..."
kubectl apply -f kibana.yaml

print_info "Waiting for Kibana to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/kibana -n logging

# Step 8: Deploy Streamlit application
print_info "Deploying Streamlit application..."
kubectl apply -f k8s-deployment.yaml

print_info "Waiting for Streamlit app to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/streamlit-app

# Step 9: Display access information
echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""

print_info "Getting service URLs..."
echo ""

# Get LoadBalancer URL for Streamlit
print_info "Streamlit App LoadBalancer URL:"
STREAMLIT_LB=$(kubectl get svc streamlit-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "Pending...")
if [ "$STREAMLIT_LB" == "Pending..." ]; then
    print_warning "LoadBalancer is still provisioning. Run this command to check status:"
    echo "kubectl get svc streamlit-service"
else
    echo "http://$STREAMLIT_LB"
fi

echo ""

# Get NodePort for Kibana
print_info "Kibana Access Options:"
echo "Option 1 (NodePort): Get any node's public IP and access http://<NODE_IP>:30601"
kubectl get nodes -o wide

echo ""
echo "Option 2 (Port Forward): Run this command and access http://localhost:5601"
echo "kubectl port-forward -n logging svc/kibana 5601:5601"

echo ""
echo "=========================================="
print_info "Next Steps:"
echo "1. Access Streamlit app and test travel itinerary generation"
echo "2. Access Kibana and create index pattern 'filebeat-*'"
echo "3. View logs in Kibana Discover"
echo ""
print_info "To view all pods:"
echo "kubectl get pods --all-namespaces"
echo ""
print_info "To view logs:"
echo "kubectl logs -l app=streamlit"
echo "kubectl logs -n logging deployment/kibana"
echo "=========================================="
