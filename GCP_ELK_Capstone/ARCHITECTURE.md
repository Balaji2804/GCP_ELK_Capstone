# Architecture Overview - AI Travel Agent on AWS EKS

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AWS Cloud (us-east-1)                              │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        Amazon EKS Cluster                               │ │
│  │                     (ai-travel-agent)                                   │ │
│  │                                                                         │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │  │                    Default Namespace                             │  │ │
│  │  │                                                                  │  │ │
│  │  │  ┌──────────────────────────────────────────────────────────┐  │  │ │
│  │  │  │  Streamlit Application Pod                               │  │ │ │
│  │  │  │  ┌────────────────────────────────────────────────────┐  │  │ │ │
│  │  │  │  │  Container: streamlit-container                    │  │  │ │ │
│  │  │  │  │  Image: ECR/streamlit-app:latest                   │  │  │ │ │
│  │  │  │  │  Port: 8501                                        │  │  │ │ │
│  │  │  │  │  ─────────────────────────────────────────────     │  │  │ │ │
│  │  │  │  │  • Python 3.10                                     │  │  │ │ │
│  │  │  │  │  • Streamlit UI                                    │  │  │ │ │
│  │  │  │  │  • LangChain + Groq LLM                            │  │  │ │ │
│  │  │  │  │  • Travel Planner Logic                            │  │  │ │ │
│  │  │  │  │                                                    │  │  │ │ │
│  │  │  │  │  Env: GROQ_API_KEY (from Secret)                  │  │  │ │ │
│  │  │  │  │  Logs → stdout → Filebeat                         │  │  │ │ │
│  │  │  │  └────────────────────────────────────────────────────┘  │  │ │ │
│  │  │  └──────────────────────────────────────────────────────────┘  │  │ │
│  │  │                                                                  │  │ │
│  │  │  ┌──────────────────────────────────────────────────────────┐  │  │ │
│  │  │  │  Service: streamlit-service                              │  │  │ │
│  │  │  │  Type: LoadBalancer                                      │  │  │ │
│  │  │  │  Port: 80 → TargetPort: 8501                            │  │  │ │
│  │  │  └──────────────────────────────────────────────────────────┘  │  │ │
│  │  │                            │                                     │  │ │
│  │  └────────────────────────────┼─────────────────────────────────────┘  │ │
│  │                               │                                        │ │
│  │                               ▼                                        │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │  │  Elastic Load Balancer (ELB)                                    │  │ │
│  │  │  External IP: xxx.xxx.xxx.xxx or DNS name                       │  │ │
│  │  │  Port 80 (HTTP)                                                 │  │ │
│  │  └─────────────────────────────────────────────────────────────────┘  │ │
│  │                               │                                        │ │
│  │  ═════════════════════════════════════════════════════════════════════ │ │
│  │                                                                         │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │  │                    Logging Namespace                             │  │ │
│  │  │                                                                  │  │ │
│  │  │  ┌────────────────────────┐    ┌──────────────────────────┐   │  │ │
│  │  │  │  Elasticsearch Pod    │◄───│  Logstash Pod            │   │  │ │
│  │  │  │  ─────────────────    │    │  ────────────────        │   │  │ │
│  │  │  │  Port: 9200           │    │  Port: 5044 (input)      │   │  │ │
│  │  │  │  Storage: 2GB EBS     │    │  Port: 9600 (monitoring) │   │  │ │
│  │  │  │  (PVC: gp2)           │    │                          │   │  │ │
│  │  │  │                       │    │  Processes & forwards    │   │  │ │
│  │  │  │  Stores all logs      │    │  logs to Elasticsearch   │   │  │ │
│  │  │  │  Indices: filebeat-*  │    │                          │   │  │ │
│  │  │  └────────────────────────┘    └──────────────────────────┘   │  │ │
│  │  │           ▲                              ▲                      │  │ │
│  │  │           │                              │                      │  │ │
│  │  │  ┌────────┴──────────────────────────────┴─────────────────┐  │  │ │
│  │  │  │  Kibana Pod                                              │  │  │ │
│  │  │  │  ───────────────                                         │  │  │ │
│  │  │  │  Port: 5601                                              │  │  │ │
│  │  │  │  Web UI for viewing logs                                 │  │  │ │
│  │  │  │                                                           │  │  │ │
│  │  │  │  Service: NodePort 30601                                 │  │  │ │
│  │  │  └───────────────────────────────────────────────────────────┘  │  │ │
│  │  │           │                              ▲                      │  │ │
│  │  │           │                              │                      │  │ │
│  │  │  ┌────────┴──────────────────────────────┴─────────────────┐  │  │ │
│  │  │  │  Filebeat DaemonSet (runs on every node)                │  │  │ │
│  │  │  │  ────────────────────────────────────                   │  │  │ │
│  │  │  │  Collects logs from:                                     │  │  │ │
│  │  │  │  /var/log/containers/*.log                               │  │  │ │
│  │  │  │                                                           │  │  │ │
│  │  │  │  Sends to Logstash:5044                                  │  │  │ │
│  │  │  │  Adds Kubernetes metadata                                │  │  │ │
│  │  │  └───────────────────────────────────────────────────────────┘  │  │ │
│  │  └──────────────────────────────────────────────────────────────────┘  │ │
│  │                                                                         │ │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │  │  Worker Nodes (2x t3.medium EC2 instances)                      │  │ │
│  │  │  • Docker runtime                                                │  │ │
│  │  │  • kubelet                                                       │  │ │
│  │  │  • Container logs → /var/log/containers/                        │  │ │
│  │  └─────────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  Supporting AWS Services                                                │ │
│  │                                                                          │ │
│  │  • Amazon ECR (Elastic Container Registry)                              │ │
│  │    └─ Docker image: streamlit-app:latest                                │ │
│  │                                                                          │ │
│  │  • Amazon EBS (Elastic Block Store)                                     │ │
│  │    └─ 2GB gp2 volume for Elasticsearch data                             │ │
│  │                                                                          │ │
│  │  • AWS Secrets Manager / K8s Secrets                                    │ │
│  │    └─ GROQ_API_KEY                                                      │ │
│  │                                                                          │ │
│  │  • AWS IAM                                                               │ │
│  │    └─ EKS cluster role, Node group role                                 │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘

                                    ▲
                                    │
                        ┌───────────┴───────────┐
                        │                       │
                ┌───────┴────────┐     ┌────────┴────────┐
                │  User Browser  │     │  User Browser   │
                │  (Streamlit)   │     │  (Kibana)       │
                │                │     │                 │
                │  http://ELB/   │     │ http://NODE:    │
                │                │     │      30601      │
                └────────────────┘     └─────────────────┘
                 Port 80                Port 30601
              (Travel Planner)         (Log Viewer)
```

---

## Data Flow Diagrams

### 1. User Request Flow (Streamlit App)

```
┌──────┐
│ User │
└──┬───┘
   │ 1. Opens http://LOADBALANCER
   ▼
┌────────────────────┐
│  AWS Load Balancer │
│  (Port 80)         │
└──┬─────────────────┘
   │ 2. Routes to
   ▼
┌──────────────────────────┐
│  Streamlit Service       │
│  (ClusterIP: 8501)       │
└──┬───────────────────────┘
   │ 3. Forwards to
   ▼
┌──────────────────────────────────┐
│  Streamlit Pod                   │
│  • Receives: City, Interests     │
│  • Calls: Groq LLM via API       │
│  • Returns: Itinerary            │
└──┬───────────────────────────────┘
   │ 4. Logs to stdout
   ▼
┌──────────────────────────┐
│  Container Logs          │
│  /var/log/containers/    │
└──────────────────────────┘
```

### 2. Log Collection Flow (ELK Stack)

```
┌────────────────────────────────┐
│  Streamlit Container           │
│  Logs written to stdout/stderr │
└──┬─────────────────────────────┘
   │ 1. Container runtime writes to
   ▼
┌───────────────────────────────────┐
│  /var/log/containers/*.log        │
│  (on worker node filesystem)      │
└──┬────────────────────────────────┘
   │ 2. Filebeat monitors & reads
   ▼
┌────────────────────────────────────┐
│  Filebeat DaemonSet                │
│  • Adds Kubernetes metadata        │
│  • Tags with pod name, namespace   │
└──┬─────────────────────────────────┘
   │ 3. Sends to Logstash:5044
   ▼
┌────────────────────────────────────┐
│  Logstash                          │
│  • Receives via beats input        │
│  • Processes (optional filters)    │
└──┬─────────────────────────────────┘
   │ 4. Indexes to Elasticsearch
   ▼
┌────────────────────────────────────┐
│  Elasticsearch                     │
│  • Stores in filebeat-* indices    │
│  • Provides search API             │
└──┬─────────────────────────────────┘
   │ 5. Kibana queries
   ▼
┌────────────────────────────────────┐
│  Kibana Web UI                     │
│  • User views logs via browser     │
│  • Accessible on NodePort 30601    │
└────────────────────────────────────┘
   ▲
   │ 6. User accesses via browser
   │
┌──┴───┐
│ User │
└──────┘
```

---

## Network Flow & Ports

```
External Access:
─────────────────────────────────────────────────────
Internet → ELB:80 → Streamlit Service → Pod:8501
Internet → NodeIP:30601 → Kibana Service → Pod:5601


Internal Cluster Communication:
─────────────────────────────────────────────────────
Filebeat → Logstash:5044
Logstash → Elasticsearch:9200
Kibana → Elasticsearch:9200


Port Mapping Table:
─────────────────────────────────────────────────────
Component        Internal Port   External Access
───────────────────────────────────────────────────
Streamlit        8501           LoadBalancer:80
Kibana           5601           NodePort:30601
Elasticsearch    9200           None (internal)
Logstash         5044           None (internal)
Logstash Mon     9600           None (internal)
```

---

## Kubernetes Resources Overview

```
Namespaces:
├── default
│   ├── Deployment: streamlit-app (1 replica)
│   ├── Service: streamlit-service (LoadBalancer)
│   └── Secret: llmops-secrets (GROQ_API_KEY)
│
└── logging
    ├── Deployment: elasticsearch (1 replica)
    ├── Service: elasticsearch (ClusterIP)
    ├── PVC: elasticsearch-pvc (2GB gp2)
    ├── Deployment: logstash (1 replica)
    ├── Service: logstash (ClusterIP)
    ├── ConfigMap: logstash-config
    ├── Deployment: kibana (1 replica)
    ├── Service: kibana (NodePort 30601)
    ├── DaemonSet: filebeat (runs on all nodes)
    ├── ConfigMap: filebeat-config
    ├── ServiceAccount: filebeat
    ├── ClusterRole: filebeat
    ├── ClusterRoleBinding: filebeat
    ├── Role: filebeat
    └── RoleBinding: filebeat
```

---

## Security Groups & IAM

```
┌──────────────────────────────────────────┐
│  EKS Cluster Security Group              │
│  ─────────────────────────────────────   │
│  • Inbound: 443 (API Server)             │
│  • Managed by AWS                        │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│  Worker Node Security Group              │
│  ─────────────────────────────────────   │
│  • Inbound: 22 (SSH - optional)          │
│  • Inbound: 30601 (Kibana NodePort) ← ADD THIS MANUALLY
│  • Inbound: 1025-65535 (NodePort range)  │
│  • Outbound: All                         │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│  IAM Roles                                │
│  ─────────────────────────────────────   │
│  • EKS Cluster Role                      │
│  • EKS Node Group Role                   │
│  • Required policies:                    │
│    - AmazonEKSClusterPolicy              │
│    - AmazonEKSWorkerNodePolicy           │
│    - AmazonEC2ContainerRegistryReadOnly  │
│    - AmazonEKS_CNI_Policy                │
└──────────────────────────────────────────┘
```

---

## Storage Architecture

```
Elasticsearch Persistent Volume:
──────────────────────────────────────────

PersistentVolumeClaim (PVC)
     └─ Name: elasticsearch-pvc
     └─ Size: 2GB
     └─ StorageClass: gp2 (AWS EBS)
     └─ AccessMode: ReadWriteOnce
          │
          ▼
AWS EBS Volume (gp2)
     └─ Type: General Purpose SSD
     └─ IOPS: 100 (baseline)
     └─ Mounted to: /usr/share/elasticsearch/data
     └─ Stores: filebeat-* indices
```

---

## High-Level Component Responsibilities

```
┌─────────────────────────────────────────────────────────┐
│  Streamlit App                                          │
│  ─────────────────────────────────────────────────────  │
│  Role: User-facing web application                      │
│  • Accepts user input (city, interests)                 │
│  • Calls Groq LLM API to generate itinerary             │
│  • Displays results to user                             │
│  • Writes logs to stdout                                │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Filebeat                                               │
│  ─────────────────────────────────────────────────────  │
│  Role: Log shipper (collector)                          │
│  • Runs on every node (DaemonSet)                       │
│  • Monitors /var/log/containers/*.log                   │
│  • Adds Kubernetes metadata (pod name, namespace, etc)  │
│  • Sends logs to Logstash                               │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Logstash                                               │
│  ─────────────────────────────────────────────────────  │
│  Role: Log processor (pipeline)                         │
│  • Receives logs from Filebeat on port 5044             │
│  • Processes and filters logs (optional transformations)│
│  • Sends processed logs to Elasticsearch                │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Elasticsearch                                          │
│  ─────────────────────────────────────────────────────  │
│  Role: Log storage & search engine                      │
│  • Stores logs in indices (filebeat-YYYY.MM.DD)         │
│  • Provides RESTful search API                          │
│  • Persists data to EBS volume                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Kibana                                                 │
│  ─────────────────────────────────────────────────────  │
│  Role: Log visualization & analysis UI                  │
│  • Queries Elasticsearch for logs                       │
│  • Provides web UI for viewing, searching, filtering    │
│  • Creates dashboards and visualizations                │
└─────────────────────────────────────────────────────────┘
```

---

## Access Patterns

```
User Accessing Streamlit App:
──────────────────────────────
User → Internet → AWS ELB → Streamlit Service → Pod
       (Browser)   (Port 80)   (Port 8501)


User Accessing Kibana (Option 1 - NodePort):
─────────────────────────────────────────────
User → Internet → Node Public IP:30601 → Kibana Service → Pod
       (Browser)                    (NodePort)


User Accessing Kibana (Option 2 - Port Forward):
─────────────────────────────────────────────────
User → Internet → EC2 Public IP:5601 → kubectl port-forward → Kibana Pod
       (Browser)  (via SSH tunnel)
```

---

## Scaling Considerations

```
Current Setup (Development):
────────────────────────────
• Streamlit: 1 replica
• Elasticsearch: 1 replica, 2GB storage
• Logstash: 1 replica
• Kibana: 1 replica
• Filebeat: DaemonSet (1 per node)
• Worker Nodes: 2x t3.medium

Production Recommendations:
────────────────────────────
• Streamlit: 3+ replicas with HPA
• Elasticsearch: 3-node cluster, 50GB+ storage per node
• Logstash: 2+ replicas
• Kibana: 2 replicas
• Filebeat: DaemonSet (scales with nodes)
• Worker Nodes: 3+ nodes (different AZs)
• Add Ingress Controller (NGINX/ALB)
• Add cert-manager for TLS
• Enable authentication for Elasticsearch/Kibana
```

This architecture provides a complete view of how all components interact in the AWS EKS environment!
