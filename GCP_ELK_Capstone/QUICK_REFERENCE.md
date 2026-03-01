# AWS EKS Deployment - Quick Reference

## ⚡ Quick Start Commands

### 1. Create EKS Cluster
```bash
eksctl create cluster --name ai-travel-agent --region us-east-1 --node-type t3.medium --nodes 2 --managed
```

### 2. Create Namespace
```bash
kubectl create namespace logging
```

### 3. Build & Push Docker Image
```bash
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=us-east-1

aws ecr create-repository --repository-name streamlit-app --region $AWS_REGION

aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

docker build -t streamlit-app:latest .
docker tag streamlit-app:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/streamlit-app:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/streamlit-app:latest
```

### 4. Update k8s-deployment.yaml
```bash
sed -i "s|<AWS_ACCOUNT_ID>|$AWS_ACCOUNT_ID|g" k8s-deployment.yaml
sed -i "s|<REGION>|$AWS_REGION|g" k8s-deployment.yaml
```

### 5. Create Secrets
```bash
kubectl create secret generic llmops-secrets --from-literal=GROQ_API_KEY=your_key_here
```

### 6. Deploy Everything
```bash
kubectl apply -f elasticsearch.yaml
kubectl apply -f logstash.yaml
kubectl apply -f filebeat.yaml
kubectl apply -f kibana.yaml
kubectl apply -f k8s-deployment.yaml
```

---

## 🔌 Port Access Guide

### Streamlit App
```bash
# Get LoadBalancer URL (wait 2-3 minutes after deployment)
kubectl get svc streamlit-service
# Access: http://<EXTERNAL-IP>
```

### Kibana - Option 1: NodePort (30601)
```bash
# Get node IP
kubectl get nodes -o wide
# Access: http://<NODE_EXTERNAL_IP>:30601

# Open port 30601 in security group:
aws ec2 authorize-security-group-ingress \
  --group-id <sg-id> \
  --protocol tcp \
  --port 30601 \
  --cidr 0.0.0.0/0
```

### Kibana - Option 2: Port Forward
```bash
kubectl port-forward -n logging svc/kibana 5601:5601 --address 0.0.0.0
# Access: http://<EC2_PUBLIC_IP>:5601
```

### Kibana - Option 3: Change to LoadBalancer
```bash
kubectl patch svc kibana -n logging -p '{"spec":{"type":"LoadBalancer"}}'
kubectl get svc kibana -n logging
# Access: http://<KIBANA_EXTERNAL_IP>:5601
```

---

## 📊 Kibana Setup for Viewing Logs

### Step-by-Step:
1. **Open Kibana**: http://<KIBANA_URL>:5601
2. **Click**: "Explore on my own"
3. **Navigate**: Menu → Management → Stack Management
4. **Click**: Index Patterns (under Kibana)
5. **Create Pattern**:
   - Index pattern: `filebeat-*`
   - Time field: `@timestamp`
   - Click "Create index pattern"
6. **View Logs**: Menu → Discover
7. **Filter App Logs**:
   - Add filter: `kubernetes.container.name is streamlit-container`

---

## 🔍 Troubleshooting Commands

### Check Pod Status
```bash
kubectl get pods --all-namespaces
kubectl get pods -l app=streamlit
kubectl get pods -n logging
kubectl describe pod <pod-name> -n <namespace>
```

### View Logs
```bash
# Streamlit app logs
kubectl logs -l app=streamlit --tail=100 -f

# Elasticsearch logs
kubectl logs -n logging deployment/elasticsearch --tail=100

# Kibana logs
kubectl logs -n logging deployment/kibana --tail=100

# Filebeat logs
kubectl logs -n logging daemonset/filebeat --tail=50
```

### Check Services
```bash
kubectl get svc --all-namespaces
kubectl describe svc streamlit-service
kubectl describe svc kibana -n logging
```

### Test Elasticsearch
```bash
kubectl port-forward -n logging svc/elasticsearch 9200:9200
# In another terminal:
curl http://localhost:9200/_cluster/health?pretty
```

### Check Events
```bash
kubectl get events --all-namespaces --sort-by='.lastTimestamp'
kubectl get events -n logging
```

---

## 🗑️ Cleanup

### Delete Kubernetes Resources
```bash
kubectl delete -f k8s-deployment.yaml
kubectl delete -f filebeat.yaml
kubectl delete -f kibana.yaml
kubectl delete -f logstash.yaml
kubectl delete -f elasticsearch.yaml
kubectl delete namespace logging
```

### Delete EKS Cluster
```bash
eksctl delete cluster --name ai-travel-agent --region us-east-1
```

### Delete ECR Repository
```bash
aws ecr delete-repository --repository-name streamlit-app --region us-east-1 --force
```

---

## 📋 Port Summary Table

| Service | Internal Port | External Access | Notes |
|---------|--------------|-----------------|-------|
| **Streamlit** | 8501 | LoadBalancer:80 | Main app |
| **Elasticsearch** | 9200 | ClusterIP (internal) | No external access |
| **Kibana** | 5601 | NodePort:30601 | Log viewer |
| **Logstash** | 5044 | ClusterIP (internal) | Receives from Filebeat |
| **Filebeat** | N/A | DaemonSet | Collects logs |

---

## 🎯 Testing Checklist

- [ ] EKS cluster created and nodes are Ready
- [ ] Docker image built and pushed to ECR
- [ ] All pods in 'Running' state
- [ ] Streamlit LoadBalancer has EXTERNAL-IP
- [ ] Can access Streamlit app via browser
- [ ] Can access Kibana via NodePort or port-forward
- [ ] Index pattern 'filebeat-*' created in Kibana
- [ ] Logs visible in Kibana Discover
- [ ] Filter shows streamlit-container logs
- [ ] Test travel itinerary generation in app
- [ ] Verify logs appear in Kibana after app usage

---

## 💰 Cost Breakdown (us-east-1)

| Resource | Cost | Notes |
|----------|------|-------|
| EKS Control Plane | $73/month | Fixed cost |
| 2x t3.medium nodes | ~$60/month | ~$0.0416/hour each |
| LoadBalancer (ELB) | ~$16/month | +data transfer |
| EBS Storage (2GB) | ~$0.20/month | $0.10/GB |
| ECR Storage | ~$0.10/month | $0.10/GB |
| **Total** | **~$150/month** | Approximate |

💡 **Tip**: Delete cluster when not in use to save costs!

---

## 🚀 Automated Deployment

Run the provided script:
```bash
chmod +x deploy-to-aws.sh
./deploy-to-aws.sh
```

---

## 📚 Important Files Modified for AWS

1. **elasticsearch.yaml** - Changed storageClassName from 'standard' to 'gp2'
2. **k8s-deployment.yaml** - Updated image URL to use ECR format

---

## 🔐 Security Notes

- Restrict NodePort 30601 to your IP only
- Use IAM roles for service accounts
- Rotate GROQ_API_KEY regularly
- Enable EKS audit logging
- Keep Elastic stack versions updated
