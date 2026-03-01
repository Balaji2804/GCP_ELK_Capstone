# Quick Restart Guide - AI Travel Agent on AWS EKS

This guide helps you quickly restart and access all services after your AWS sandbox environment stops/terminates resources.

---

## Prerequisites Check

```bash
# 1. SSH into your EC2 management instance
ssh -i your-key.pem ec2-user@<EC2_PUBLIC_IP>

# 2. Verify AWS credentials
aws sts get-caller-identity

# 3. Verify kubectl is configured
kubectl config current-context
```

---

## Step 1: Check Cluster Status

```bash
# Check if cluster is running
aws eks describe-cluster --name ai-travel-agent --region ap-south-1 --query 'cluster.status'
# Should show: "ACTIVE"

# Check nodes
kubectl get nodes
# Should show 2 nodes in Ready state

# If nodes are not Ready, wait 2-3 minutes for them to initialize
```

---

## Step 2: Check and Restart Pods (if needed)

### Check All Pods Status

```bash
# Check logging namespace (ELK Stack)
kubectl get pods -n logging

# Check default namespace (Streamlit app)
kubectl get pods

# Expected output:
# NAMESPACE   NAME                             READY   STATUS    AGE
# logging     elasticsearch-xxxxx              1/1     Running   XXm
# logging     kibana-xxxxx                     1/1     Running   XXm
# logging     logstash-xxxxx                   1/1     Running   XXm
# logging     filebeat-xxxxx (2 pods)          1/1     Running   XXm
# default     streamlit-app-xxxxx              1/1     Running   XXm
```

### Restart Pods if Not Running

```bash
# Restart Elasticsearch
kubectl rollout restart deployment elasticsearch -n logging

# Restart Kibana
kubectl rollout restart deployment kibana -n logging

# Restart Logstash
kubectl rollout restart deployment logstash -n logging

# Restart Filebeat
kubectl rollout restart daemonset filebeat -n logging

# Restart Streamlit App
kubectl rollout restart deployment streamlit-app

# Wait for all pods to be Running (2-3 minutes)
kubectl get pods -n logging -w
# Press Ctrl+C when all show 1/1 Running
```

---

## Step 3: Configure Security Group (First Time Only)

**Only needed once** - if you haven't added these rules yet:

```bash
# Get your EC2 instance details
export INSTANCE_ID=$(ec2-metadata --instance-id | cut -d ' ' -f 2)
export SG_ID=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' --output text)

# Add inbound rules for ports (allow from anywhere or restrict to your IP)
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 8501 --cidr 0.0.0.0/0 --region ap-south-1  # Streamlit
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 5601 --cidr 0.0.0.0/0 --region ap-south-1  # Kibana
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 9200 --cidr 0.0.0.0/0 --region ap-south-1  # Elasticsearch (optional)

# Verify rules were added
aws ec2 describe-security-groups --group-ids $SG_ID --query 'SecurityGroups[0].IpPermissions' --region ap-south-1
```

**Note:** If rules already exist, you'll get a "duplicate" error - that's OK!

---

## Step 4: Start Port Forwarding

### Kill Existing Port-Forward Processes (if any)

```bash
# Check for existing port-forward processes
ps aux | grep "port-forward"

# Kill them if found
pkill -f "port-forward"

# Verify they're gone
jobs
```

### Start All Port-Forwards

```bash
# Start Streamlit (port 8501)
kubectl port-forward svc/streamlit-service 8501:80 --address 0.0.0.0 > /tmp/streamlit-pf.log 2>&1 &

# Start Kibana (port 5601)
kubectl port-forward -n logging svc/kibana 5601:5601 --address 0.0.0.0 > /tmp/kibana-pf.log 2>&1 &

# Start Elasticsearch (port 9200) - Optional
kubectl port-forward -n logging svc/elasticsearch 9200:9200 --address 0.0.0.0 > /tmp/elasticsearch-pf.log 2>&1 &

# Verify all are running
jobs
# Should show 2-3 background jobs

# Check logs if any fail
tail /tmp/streamlit-pf.log
tail /tmp/kibana-pf.log
tail /tmp/elasticsearch-pf.log
```

---

## Step 5: Access Services

### Get Your EC2 Public IP

```bash
# Method 1
curl http://checkip.amazonaws.com

# Method 2
ec2-metadata --public-ipv4 | cut -d ' ' -f 2

# Method 3 (from AWS CLI)
aws ec2 describe-instances --instance-ids $(ec2-metadata --instance-id | cut -d ' ' -f 2) \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text --region ap-south-1
```

### Access URLs

Open in your browser:

- **Streamlit App**: `http://<EC2_PUBLIC_IP>:8501`
- **Kibana Dashboard**: `http://<EC2_PUBLIC_IP>:5601`
- **Elasticsearch API**: `http://<EC2_PUBLIC_IP>:9200` (optional)

---

## Step 6: Verify Everything Works

### Test Streamlit App

1. Go to `http://<EC2_PUBLIC_IP>:8501`
2. Enter a city: **Paris**
3. Enter interests: **museums, food**
4. Click **Generate Itinerary**
5. Should see AI-generated travel plan

### Test Kibana

1. Go to `http://<EC2_PUBLIC_IP>:5601`
2. Click **Explore on my own**
3. Go to **Management** → **Stack Management** → **Index Patterns**
4. Create index pattern: `filebeat-*`
5. Click **Discover** to view logs

### Test Elasticsearch

```bash
# From EC2 terminal
curl http://localhost:9200/_cluster/health?pretty

# Should show:
# "status" : "green"
# "active_shards_percent_as_number" : 100.0
```

---

## Quick Commands Reference

### Check Status

```bash
# All pods status
kubectl get pods --all-namespaces

# Services
kubectl get svc --all-namespaces

# Nodes
kubectl get nodes -o wide

# Port-forward processes
jobs
ps aux | grep port-forward
```

### View Logs

```bash
# Streamlit logs
kubectl logs -l app=streamlit --tail=50

# Elasticsearch logs
kubectl logs -n logging deployment/elasticsearch --tail=50

# Kibana logs
kubectl logs -n logging deployment/kibana --tail=50

# Filebeat logs
kubectl logs -n logging daemonset/filebeat --tail=50
```

### Restart Everything

```bash
# Restart all ELK components
kubectl rollout restart deployment elasticsearch -n logging
kubectl rollout restart deployment kibana -n logging
kubectl rollout restart deployment logstash -n logging
kubectl rollout restart daemonset filebeat -n logging

# Restart Streamlit app
kubectl rollout restart deployment streamlit-app

# Restart port-forwards
pkill -f "port-forward"
kubectl port-forward svc/streamlit-service 8501:80 --address 0.0.0.0 &
kubectl port-forward -n logging svc/kibana 5601:5601 --address 0.0.0.0 &
kubectl port-forward -n logging svc/elasticsearch 9200:9200 --address 0.0.0.0 &
```

### Stop Port-Forwards

```bash
# Kill all port-forward processes
pkill -f "port-forward"

# Or stop specific port-forward
jobs  # Note the job number
kill %1  # Replace 1 with actual job number
```

---

## Troubleshooting

### Pods Not Starting

```bash
# Check pod details
kubectl describe pod <pod-name> -n <namespace>

# Check if nodes have taints
kubectl describe nodes | grep -A 5 Taints

# Verify tolerations are in place
kubectl get deployment elasticsearch -n logging -o yaml | grep -A 5 tolerations
```

### Port-Forward Fails

```bash
# Check if port is already in use
netstat -tlnp | grep 8501
netstat -tlnp | grep 5601

# Kill process using the port
fuser -k 8501/tcp
fuser -k 5601/tcp

# Restart port-forward
kubectl port-forward svc/streamlit-service 8501:80 --address 0.0.0.0 &
```

### Can't Access from Browser

```bash
# 1. Verify security group rules exist
aws ec2 describe-security-groups --group-ids $SG_ID --region ap-south-1

# 2. Verify port-forward is running
jobs
ps aux | grep port-forward

# 3. Test from EC2 instance
curl http://localhost:8501
curl http://localhost:5601

# 4. Verify EC2 public IP is correct
curl http://checkip.amazonaws.com
```

### Elasticsearch Not Healthy

```bash
# Check health
kubectl exec -n logging deployment/elasticsearch -- curl localhost:9200/_cluster/health?pretty

# If status is "red" or "yellow", restart
kubectl rollout restart deployment elasticsearch -n logging

# Wait 2-3 minutes and check again
```

---

## Complete Restart Script

Save this as `restart-all.sh` for quick restart:

```bash
#!/bin/bash

echo "=== Checking Cluster Status ==="
kubectl get nodes

echo -e "\n=== Checking Pods ==="
kubectl get pods --all-namespaces

echo -e "\n=== Restarting All Services ==="
kubectl rollout restart deployment elasticsearch -n logging
kubectl rollout restart deployment kibana -n logging
kubectl rollout restart deployment logstash -n logging
kubectl rollout restart daemonset filebeat -n logging
kubectl rollout restart deployment streamlit-app

echo -e "\n=== Waiting for pods to be ready (60 seconds) ==="
sleep 60

echo -e "\n=== Killing existing port-forwards ==="
pkill -f "port-forward"

echo -e "\n=== Starting port-forwards ==="
kubectl port-forward svc/streamlit-service 8501:80 --address 0.0.0.0 > /tmp/streamlit-pf.log 2>&1 &
kubectl port-forward -n logging svc/kibana 5601:5601 --address 0.0.0.0 > /tmp/kibana-pf.log 2>&1 &
kubectl port-forward -n logging svc/elasticsearch 9200:9200 --address 0.0.0.0 > /tmp/elasticsearch-pf.log 2>&1 &

echo -e "\n=== Verifying port-forwards ==="
sleep 5
jobs

echo -e "\n=== Getting EC2 Public IP ==="
PUBLIC_IP=$(curl -s http://checkip.amazonaws.com)
echo "EC2 Public IP: $PUBLIC_IP"

echo -e "\n=== Access URLs ==="
echo "Streamlit App: http://$PUBLIC_IP:8501"
echo "Kibana: http://$PUBLIC_IP:5601"
echo "Elasticsearch: http://$PUBLIC_IP:9200"

echo -e "\n=== All services restarted! ==="
```

**Usage:**
```bash
chmod +x restart-all.sh
./restart-all.sh
```

---

## Summary

**After sandbox restart, run these 4 commands:**

```bash
# 1. Check cluster
kubectl get nodes

# 2. Kill old port-forwards
pkill -f "port-forward"

# 3. Start port-forwards
kubectl port-forward svc/streamlit-service 8501:80 --address 0.0.0.0 &
kubectl port-forward -n logging svc/kibana 5601:5601 --address 0.0.0.0 &

# 4. Get IP and access
curl http://checkip.amazonaws.com
# Open: http://<IP>:8501 and http://<IP>:5601
```

**Done! Your AI Travel Agent is accessible!** 🚀
