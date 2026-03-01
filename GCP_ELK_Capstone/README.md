# 🌍 AI Travel Itinerary Planner

An intelligent travel planning application powered by Large Language Models (LLMs) that generates personalized day trip itineraries based on your destination and interests. Built with Streamlit, LangChain, and Groq API, deployed on AWS EKS with comprehensive ELK stack logging.

![Python](https://img.shields.io/badge/python-3.10-blue)
![Streamlit](https://img.shields.io/badge/streamlit-1.x-red)
![AWS](https://img.shields.io/badge/AWS-EKS-orange)
![Kubernetes](https://img.shields.io/badge/kubernetes-1.28-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ Features

- 🤖 **AI-Powered Itineraries**: Uses Groq's LLama 3.3 70B model for intelligent travel planning
- 🎨 **User-Friendly Interface**: Clean Streamlit web interface
- 🔍 **Personalized Suggestions**: Tailored recommendations based on your interests
- 📊 **Comprehensive Logging**: Full ELK stack (Elasticsearch, Logstash, Kibana, Filebeat)
- ☁️ **Cloud-Native**: Kubernetes deployment on AWS EKS
- 🐳 **Containerized**: Docker-based deployment
- 🔄 **Scalable**: Ready for production scaling

---

## 🚀 Quick Demo

1. Enter your destination city (e.g., "New York", "Paris", "Tokyo")
2. List your interests (e.g., "museums, food, nature")
3. Click "Generate Itinerary"
4. Receive a personalized day trip plan instantly!

---

## 🏗️ Architecture

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       ▼
┌──────────────────┐      ┌───────────────┐
│  Streamlit App   │─────→│  Groq LLM API │
│  (Port 8501)     │      │  (External)   │
└──────┬───────────┘      └───────────────┘
       │ Logs
       ▼
┌──────────────────┐
│  ELK Stack       │
│  ├─ Filebeat     │ (Collect)
│  ├─ Logstash     │ (Process)
│  ├─ Elasticsearch│ (Store)
│  └─ Kibana       │ (Visualize)
└──────────────────┘
```

**Detailed Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md)

---

## 📋 Prerequisites

- **AWS Account** with appropriate IAM permissions
- **GROQ API Key** - Get from [Groq Console](https://console.groq.com)
- **Basic Tools**:
  - Docker
  - kubectl
  - eksctl
  - AWS CLI (configured)

---

## 🎯 AWS Deployment (No GCP Required!)

### ✅ Feasibility: **100% Compatible with AWS**

This project was originally designed for GCP but contains **zero GCP-specific dependencies**. All Kubernetes manifests and Docker configurations work seamlessly on AWS EKS.

### Quick Start

```bash
# 1. Clone repository
git clone <repo-url>
cd AI_Travel_Agent

# 2. Run automated deployment
chmod +x deploy-to-aws.sh
./deploy-to-aws.sh

# 3. Get access URLs
kubectl get svc streamlit-service          # Streamlit app
kubectl get nodes -o wide                  # Kibana: http://<NODE_IP>:30601
```

### Detailed Setup

For complete step-by-step instructions:
- 📖 **[AWS Deployment Guide](AWS_DEPLOYMENT_GUIDE.md)** - Full deployment walkthrough
- ⚡ **[Quick Reference](QUICK_REFERENCE.md)** - Command cheat sheet
- 📊 **[ELK Access Guide](ELK_ACCESS_GUIDE.md)** - Log viewing tutorial

---

## 🔌 Port Configuration

| Service | Port | Access Type | Purpose |
|---------|------|-------------|---------|
| Streamlit | 80 (→8501) | LoadBalancer | Web UI |
| Kibana | 30601 | NodePort | Logs UI |
| Elasticsearch | 9200 | ClusterIP | Log Storage |
| Logstash | 5044 | ClusterIP | Log Processing |

**Security Note**: Only ports 80 (Streamlit) and 30601 (Kibana) are externally accessible.

---

## 📊 Accessing Application Logs (Your Main Goal!)

### Step 1: Access Kibana
```bash
# Get worker node IP
kubectl get nodes -o wide

# Open security group port 30601
aws ec2 authorize-security-group-ingress \
  --group-id <sg-id> \
  --protocol tcp \
  --port 30601 \
  --cidr 0.0.0.0/0

# Access Kibana
http://<NODE_IP>:30601
```

### Step 2: Configure Kibana
1. Click "Explore on my own"
2. Navigate to **Management → Index Patterns**
3. Create pattern: `filebeat-*`
4. Select time field: `@timestamp`

### Step 3: View Logs
1. Open **Discover** from menu
2. Add filter: `kubernetes.container.name: "streamlit-container"`
3. View real-time logs from your application!

**Full Tutorial**: [ELK_ACCESS_GUIDE.md](ELK_ACCESS_GUIDE.md)

---

## 🛠️ Local Development

### Option 1: Direct Python
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Set environment variable
export GROQ_API_KEY=your_api_key_here

# Run application
streamlit run app.py
```

### Option 2: Docker
```bash
# Build image
docker build -t streamlit-app:latest .

# Run container
docker run -p 8501:8501 \
  -e GROQ_API_KEY=your_api_key_here \
  streamlit-app:latest
```

Access at: http://localhost:8501

---

## 📂 Project Structure

```
AI_Travel_Agent/
├── app.py                      # Main Streamlit application
├── Dockerfile                  # Container configuration
├── requirements.txt            # Python dependencies
├── setup.py                    # Package setup
│
├── src/
│   ├── core/
│   │   └── planner.py         # Travel planning logic
│   ├── chains/
│   │   └── itinerary_chain.py # LLM chain configuration
│   ├── config/
│   │   └── config.py          # App configuration
│   └── utils/
│       ├── logger.py          # Logging utilities
│       └── custom_exception.py # Error handling
│
├── Kubernetes Manifests:
│   ├── k8s-deployment.yaml    # Streamlit app deployment
│   ├── elasticsearch.yaml     # Log storage
│   ├── logstash.yaml         # Log processing
│   ├── kibana.yaml           # Log visualization
│   └── filebeat.yaml         # Log collection
│
└── Documentation:
    ├── AWS_DEPLOYMENT_GUIDE.md
    ├── ELK_ACCESS_GUIDE.md
    ├── QUICK_REFERENCE.md
    ├── ARCHITECTURE.md
    ├── DEPLOYMENT_SUMMARY.md
    └── deploy-to-aws.sh
```

---

## 🔧 Configuration

### Environment Variables
- `GROQ_API_KEY` - Required for LLM API access

### Kubernetes Secrets
```bash
kubectl create secret generic llmops-secrets \
  --from-literal=GROQ_API_KEY=your_key_here
```

---

## 📈 Scaling

### Horizontal Pod Autoscaling
```bash
kubectl autoscale deployment streamlit-app \
  --cpu-percent=70 \
  --min=1 \
  --max=5
```

### Production Recommendations
- **Streamlit**: 3+ replicas with HPA
- **Elasticsearch**: 3-node cluster, 50GB+ per node
- **Logstash**: 2+ replicas
- **Kibana**: 2 replicas for HA
- **Worker Nodes**: 3+ nodes across multiple AZs

---

## 💰 Cost Estimate (AWS us-east-1)

| Component | Monthly Cost |
|-----------|-------------|
| EKS Control Plane | $73 |
| 2x t3.medium nodes | $60 |
| Load Balancer | $18 |
| EBS Storage (2GB) | $0.20 |
| ECR Storage | $0.10 |
| **Total** | **~$155/month** |

💡 **Tip**: Use `eksctl delete cluster` when not in use to avoid charges.

---

## 🐛 Troubleshooting

### Common Issues

**LoadBalancer Pending**
```bash
# Wait 3-5 minutes for AWS to provision ELB
kubectl describe svc streamlit-service
```

**Can't Access Kibana**
```bash
# Verify port 30601 is open in security group
kubectl get svc kibana -n logging
```

**No Logs in Kibana**
```bash
# Check Filebeat pods
kubectl get pods -n logging | grep filebeat
kubectl logs -n logging daemonset/filebeat --tail=100
```

**Pod Crashes/Errors**
```bash
# Check pod status and logs
kubectl get pods
kubectl describe pod <pod-name>
kubectl logs <pod-name> --tail=100
```

---

## 🧪 Testing

### Test Streamlit App
1. Navigate to LoadBalancer URL
2. Enter city: "San Francisco"
3. Enter interests: "technology, food, hiking"
4. Click "Generate Itinerary"
5. Verify AI-generated itinerary appears

### Test ELK Logging
1. Access Kibana on port 30601
2. Create index pattern: `filebeat-*`
3. Open Discover
4. Search for: `message: "Generating itinerary"`
5. Verify logs from your test appear

---

## 🔐 Security

- ✅ Secrets stored in Kubernetes Secrets
- ✅ Network policies for pod-to-pod communication
- ✅ Security groups restrict external access
- ⚠️ Add authentication for Kibana in production
- ⚠️ Use TLS/SSL for external endpoints

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md) | High-level overview |
| [AWS_DEPLOYMENT_GUIDE.md](AWS_DEPLOYMENT_GUIDE.md) | Complete deployment steps |
| [ELK_ACCESS_GUIDE.md](ELK_ACCESS_GUIDE.md) | Log viewing tutorial |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | Command cheat sheet |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture |

---

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 👤 Author

**Balaji Krishnan**

---

## 🙏 Acknowledgments

- [Groq](https://groq.com) - Fast LLM inference
- [LangChain](https://langchain.com) - LLM orchestration framework
- [Streamlit](https://streamlit.io) - Web framework
- [Elastic](https://elastic.co) - ELK stack components
- AWS - Cloud infrastructure

---

## 🔗 Related Links

- [Groq Documentation](https://console.groq.com/docs)
- [LangChain Documentation](https://python.langchain.com/docs/get_started/introduction)
- [Streamlit Documentation](https://docs.streamlit.io)
- [AWS EKS Documentation](https://docs.aws.amazon.com/eks/)
- [Elastic Stack on Kubernetes](https://www.elastic.co/guide/en/cloud-on-k8s/current/index.html)

---

## 📞 Support

For issues and questions:
- 📖 Check the documentation files
- 🐛 Open a GitHub issue
- 💬 Review troubleshooting section

---

## ⭐ Star This Repository

If you find this project useful, please consider giving it a star! ⭐

---

**Happy Traveling! 🌍✈️**
