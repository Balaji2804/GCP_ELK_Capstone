# AWS Deployment Summary - AI Travel Agent

## 📋 Project Overview

This repository contains an AI-powered travel itinerary planner built with:
- **Streamlit** - User interface
- **LangChain** - LLM orchestration
- **Groq API** - AI language model
- **ELK Stack** - Logging and monitoring (Elasticsearch, Logstash, Kibana, Filebeat)

**Original Platform**: Designed for GCP (but had no GCP-specific code)  
**Target Platform**: AWS EKS (fully compatible)

---

## ✅ Feasibility Analysis

### Is it feasible to deploy on AWS? **YES!**

**Reasons:**
1. ✅ No GCP-specific APIs or SDKs in the codebase
2. ✅ Standard Kubernetes manifests (work on any K8s cluster)
3. ✅ Standard Docker containerization
4. ✅ No cloud-specific storage services used
5. ✅ Only requires standard Kubernetes features

**Changes Required:**
- ✏️ Update `storageClassName` from `standard` to `gp2` (AWS EBS)
- ✏️ Update Docker image reference to AWS ECR format

**Both changes have been completed in this repository.**

---

## 📁 Documentation Files Created

| File | Purpose |
|------|---------|
| **AWS_DEPLOYMENT_GUIDE.md** | Complete step-by-step deployment guide (EC2 setup → EKS cluster → Deploy app) |
| **ELK_ACCESS_GUIDE.md** | Detailed guide to access Kibana and view logs |
| **QUICK_REFERENCE.md** | Quick commands reference and cheat sheet |
| **ARCHITECTURE.md** | System architecture diagrams and component details |
| **deploy-to-aws.sh** | Automated deployment script |
| **This File** | Summary and starting point |

---

## 🚀 Quick Start (3 Steps)

### 1. Prerequisites
- AWS account with admin access
- AWS CLI configured (`aws configure`)
- EC2 instance (t3.medium or larger) with:
  - Docker installed
  - kubectl installed
  - eksctl installed
  - Git installed

### 2. Clone and Deploy
```bash
git clone <your-repo-url>
cd AI_Travel_Agent
chmod +x deploy-to-aws.sh
./deploy-to-aws.sh
```

### 3. Access Applications
```bash
# Get Streamlit app URL
kubectl get svc streamlit-service

# Access Kibana
kubectl get nodes -o wide
# Then visit: http://<NODE_IP>:30601
```

---

## 🔌 Port Configuration

### Application Ports
| Component | Internal Port | External Access | Purpose |
|-----------|--------------|-----------------|---------|
| **Streamlit** | 8501 | LoadBalancer:80 | Travel planning UI |
| **Kibana** | 5601 | NodePort:30601 | Log viewing interface |
| **Elasticsearch** | 9200 | Internal only | Log storage |
| **Logstash** | 5044 | Internal only | Log processing |

### Security Group Requirements
- **Worker Node SG**: Open port 30601 (TCP) for Kibana access
- **LoadBalancer**: Automatically created by EKS (port 80)

---

## 📊 Accessing ELK Logs - Your Main Goal

### Quick Method (NodePort)
1. Get node IP: `kubectl get nodes -o wide`
2. Open port 30601 in security group:
   ```bash
   aws ec2 authorize-security-group-ingress \
     --group-id sg-xxxxx \
     --protocol tcp \
     --port 30601 \
     --cidr 0.0.0.0/0
   ```
3. Access: `http://<NODE_IP>:30601`

### What You'll Do in Kibana
1. Create index pattern: `filebeat-*`
2. Go to Discover
3. Filter by: `kubernetes.container.name: "streamlit-container"`
4. View your app logs in real-time!

**Full details**: See [ELK_ACCESS_GUIDE.md](ELK_ACCESS_GUIDE.md)

---

## 🗂️ Repository Structure

```
AI_Travel_Agent/
├── app.py                          # Main Streamlit application
├── Dockerfile                      # Container definition
├── requirements.txt                # Python dependencies
├── setup.py                        # Package installation
│
├── k8s-deployment.yaml             # [MODIFIED] Streamlit app K8s config
├── elasticsearch.yaml              # [MODIFIED] Elasticsearch setup
├── logstash.yaml                   # Logstash configuration
├── kibana.yaml                     # Kibana web UI
├── filebeat.yaml                   # Log collection agent
│
├── src/
│   ├── core/planner.py            # Travel planning logic
│   ├── chains/itinerary_chain.py  # LLM chain definition
│   ├── config/config.py           # Configuration
│   └── utils/                      # Logger & exceptions
│
└── Documentation (NEW):
    ├── AWS_DEPLOYMENT_GUIDE.md     # Complete deployment steps
    ├── ELK_ACCESS_GUIDE.md         # How to view logs in Kibana
    ├── QUICK_REFERENCE.md          # Command cheat sheet
    ├── ARCHITECTURE.md             # System diagrams
    ├── deploy-to-aws.sh            # Automated deployment
    └── DEPLOYMENT_SUMMARY.md       # This file
```

---

## 🛠️ Manual Deployment Steps (Overview)

### Phase 1: AWS Setup (30 min)
1. Launch EC2 instance (t3.medium)
2. Install Docker, kubectl, eksctl, AWS CLI
3. Configure AWS credentials
4. Create EKS cluster: `eksctl create cluster ...`

### Phase 2: Docker Image (10 min)
1. Create ECR repository
2. Build Docker image
3. Tag and push to ECR
4. Update k8s-deployment.yaml with ECR URL

### Phase 3: Kubernetes Deployment (15 min)
1. Create `logging` namespace
2. Create secrets (GROQ_API_KEY)
3. Apply Elasticsearch manifest
4. Apply Logstash manifest
5. Apply Filebeat manifest
6. Apply Kibana manifest
7. Apply Streamlit app manifest

### Phase 4: Access & Verify (10 min)
1. Get LoadBalancer URL for app
2. Open NodePort 30601 for Kibana
3. Create Kibana index pattern
4. Test app and view logs

**Total Time**: ~65 minutes (excluding EKS cluster creation ~20 min)

**Detailed Steps**: See [AWS_DEPLOYMENT_GUIDE.md](AWS_DEPLOYMENT_GUIDE.md)

---

## 💡 Key Differences from GCP

| Aspect | GCP | AWS |
|--------|-----|-----|
| **Kubernetes** | GKE | EKS |
| **Container Registry** | GCR | ECR |
| **Storage Class** | `standard` | `gp2` |
| **Load Balancer** | GCP LB | AWS ELB |
| **CLI Tool** | `gcloud` | `aws` |
| **Cluster Creation** | `gcloud container clusters create` | `eksctl create cluster` |

**Code Changes Required**: Minimal (only storage class and image URL)

---

## 🎯 Your Specific Requirements - Addressed

### ✅ No API Gateway
- **Solution**: Using native Kubernetes LoadBalancer service
- Streamlit app directly exposed via ELB on port 80

### ✅ No Route 53
- **Solution**: Using LoadBalancer DNS name directly
- Access via: `http://xxxxx.elb.amazonaws.com`

### ✅ ELK Log Access (Main Goal)
- **Solution**: Kibana accessible via NodePort 30601
- Full ELK stack deployed in `logging` namespace
- Filebeat collects logs → Logstash processes → Elasticsearch stores → Kibana visualizes

### ✅ Manual Steps
- All manual steps documented in AWS_DEPLOYMENT_GUIDE.md
- Automated script provided as alternative (deploy-to-aws.sh)

### ✅ EC2 Dependencies
- Complete installation guide for EC2 provided
- All required tools listed with installation commands

### ✅ EKS Deployment
- eksctl commands provided for cluster creation
- Kubernetes manifests ready to deploy
- Service configuration optimized for EKS

---

## 🔍 Verification Checklist

After deployment, verify:

- [ ] EKS cluster is active: `kubectl get nodes`
- [ ] All pods are running: `kubectl get pods --all-namespaces`
- [ ] LoadBalancer has external IP: `kubectl get svc streamlit-service`
- [ ] Can access Streamlit app in browser
- [ ] Can access Kibana UI on port 30601
- [ ] Kibana index pattern created: `filebeat-*`
- [ ] Logs visible in Kibana Discover
- [ ] Can filter logs by container name
- [ ] Generate test itinerary in Streamlit
- [ ] See new logs appear in Kibana

---

## 💰 Cost Estimate (Monthly)

| Resource | Cost |
|----------|------|
| EKS Control Plane | $73 |
| 2x t3.medium nodes (~730 hrs) | $60 |
| ELB (Classic) | $18 |
| EBS 2GB (gp2) | $0.20 |
| ECR Storage (~1GB) | $0.10 |
| Data Transfer (minimal) | $5 |
| **Total** | **~$155/month** |

**💡 Cost Saving Tip**: Delete cluster when not in use:
```bash
eksctl delete cluster --name ai-travel-agent --region us-east-1
```

---

## 🐛 Common Issues & Solutions

### Issue: LoadBalancer stuck in "Pending"
**Solution**: Wait 3-5 minutes. EKS provisions ELB automatically.

### Issue: Can't access Kibana on port 30601
**Solution**: 
```bash
# Open port in worker node security group
aws ec2 authorize-security-group-ingress \
  --group-id <sg-id> \
  --protocol tcp \
  --port 30601 \
  --cidr 0.0.0.0/0
```

### Issue: No logs in Kibana
**Solution**:
```bash
# Check Filebeat is running
kubectl get pods -n logging | grep filebeat

# Check logs
kubectl logs -n logging daemonset/filebeat --tail=100
```

### Issue: Elasticsearch pod pending
**Solution**: Check PVC is bound:
```bash
kubectl get pvc -n logging
# If pending, verify gp2 storage class exists
kubectl get storageclass
```

---

## 📚 Next Steps After Deployment

1. **Secure Kibana**: Add authentication (X-Pack or NGINX proxy)
2. **SSL/TLS**: Add HTTPS with ACM certificate (if needed)
3. **Monitoring**: Set up CloudWatch for cluster metrics
4. **Autoscaling**: Configure HPA for Streamlit pods
5. **Backup**: Set up Elasticsearch snapshots to S3
6. **Log Retention**: Configure ILM policies in Elasticsearch
7. **Alerts**: Set up Kibana alerts for errors

---

## 🔗 Important Links

- **AWS EKS Documentation**: https://docs.aws.amazon.com/eks/
- **eksctl Guide**: https://eksctl.io/
- **Elastic Stack on K8s**: https://www.elastic.co/guide/en/cloud-on-k8s/current/
- **Kubernetes Documentation**: https://kubernetes.io/docs/

---

## 📞 Support Commands

### Get status of everything:
```bash
kubectl get all --all-namespaces
```

### View recent events:
```bash
kubectl get events --all-namespaces --sort-by='.lastTimestamp' | tail -20
```

### Check cluster info:
```bash
kubectl cluster-info
eksctl get cluster
```

### View logs from a specific pod:
```bash
kubectl logs <pod-name> -n <namespace> --tail=100 -f
```

---

## ✨ Summary

**Feasibility**: ✅ **100% Feasible**  
**GCP Dependencies**: ✅ **None found**  
**AWS Compatibility**: ✅ **Fully compatible**  
**Changes Required**: ✅ **Minimal (completed)**  
**Deployment Complexity**: ⭐⭐⭐ (Medium - well documented)  
**ELK Access**: ✅ **Straightforward via NodePort**  

Your application is **ready to deploy on AWS EKS** with the provided documentation and scripts. No API Gateway or Route 53 needed. ELK logs are accessible via Kibana on NodePort 30601.

---

## 🎉 Getting Started

1. **Read**: [AWS_DEPLOYMENT_GUIDE.md](AWS_DEPLOYMENT_GUIDE.md) for complete instructions
2. **Quick Reference**: [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for commands
3. **ELK Setup**: [ELK_ACCESS_GUIDE.md](ELK_ACCESS_GUIDE.md) for log viewing
4. **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md) for system design

**Or simply run**:
```bash
./deploy-to-aws.sh
```

Good luck with your deployment! 🚀
