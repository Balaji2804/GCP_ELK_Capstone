# Step-by-Step Guide: Accessing ELK Stack Logs

## 🎯 Goal
View container logs from your AI Travel Agent app in Kibana dashboard on AWS EKS.

---

## 📋 Prerequisites Checklist
- [x] EKS cluster deployed
- [x] All pods running (check: `kubectl get pods --all-namespaces`)
- [x] Kibana pod is in Running state
- [x] Streamlit app is deployed and running

---

## 🔌 Step 1: Access Kibana UI

### Method A: NodePort (Simplest - Recommended)

1. **Get your EKS node public IP:**
```bash
kubectl get nodes -o wide
```
Look for the `EXTERNAL-IP` column.

2. **Find the node security group:**
```bash
# Get the cluster name
CLUSTER_NAME="ai-travel-agent"

# Find security groups attached to worker nodes
aws ec2 describe-instances \
  --filters "Name=tag:eks:cluster-name,Values=$CLUSTER_NAME" \
  --query 'Reservations[*].Instances[*].[InstanceId,SecurityGroups[*].GroupId]' \
  --output table
```

3. **Open port 30601 in the security group:**
```bash
# Replace <security-group-id> with actual SG ID from above
SG_ID="sg-xxxxxxxxx"

aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 30601 \
  --cidr 0.0.0.0/0

# For better security, replace 0.0.0.0/0 with your specific IP:
# --cidr <YOUR_IP>/32
```

4. **Access Kibana:**
```
http://<NODE_EXTERNAL_IP>:30601
```
Example: `http://3.84.25.123:30601`

---

### Method B: Port Forward (Alternative)

1. **From your EC2 management instance:**
```bash
kubectl port-forward -n logging svc/kibana 5601:5601 --address 0.0.0.0 &
```

2. **Open port 5601 in EC2 security group** (where you're running the command)

3. **Access Kibana:**
```
http://<EC2_PUBLIC_IP>:5601
```

---

### Method C: LoadBalancer (Costs Extra)

1. **Change Kibana service to LoadBalancer:**
```bash
kubectl patch svc kibana -n logging -p '{"spec":{"type":"LoadBalancer"}}'
```

2. **Wait 2-3 minutes, then get the URL:**
```bash
kubectl get svc kibana -n logging
```

3. **Access Kibana:**
```
http://<KIBANA_LOADBALANCER_URL>:5601
```

---

## 🎨 Step 2: Initial Kibana Setup

### 2.1 First Time Login
1. Open Kibana in your browser
2. You'll see the Kibana welcome page
3. Click **"Explore on my own"** button

### 2.2 Navigate to Index Patterns
1. Click the **hamburger menu** (≡) in the top-left corner
2. Scroll down and click **"Stack Management"** (gear icon at bottom)
3. Under "Kibana" section, click **"Index Patterns"**

---

## 📊 Step 3: Create Index Pattern for Logs

### 3.1 Create New Index Pattern
1. Click the **"Create index pattern"** button
2. In the "Index pattern name" field, type: `filebeat-*`
3. You should see a message: "Success! Your index pattern matches X indices."
4. Click **"Next step"** button

### 3.2 Configure Time Field
1. In the "Time field" dropdown, select **@timestamp**
2. Click **"Create index pattern"** button
3. You should see fields like `kubernetes.container.name`, `message`, `log`, etc.

---

## 🔍 Step 4: View Logs in Discover

### 4.1 Open Discover
1. Click the **hamburger menu** (≡) again
2. Under "Analytics", click **"Discover"**
3. Make sure **filebeat-*** is selected in the dropdown (top-left)

### 4.2 Adjust Time Range
1. Look at the top-right corner for the time picker
2. Click on the time range (default is "Last 15 minutes")
3. Select one of:
   - **Last 15 minutes** - for recent logs
   - **Last 1 hour** - for broader view
   - **Today** - for all logs today
   - **Custom** - for specific date range

### 4.3 Refresh Data
Click the **Refresh** button (circular arrow icon) to load logs

---

## 🎯 Step 5: Filter for Streamlit App Logs

### Option 1: Using Filter Button (Recommended)
1. Click the **"+ Add filter"** button below the search bar
2. Configure the filter:
   - **Field:** Select or type `kubernetes.container.name`
   - **Operator:** Select `is`
   - **Value:** Type `streamlit-container`
3. Click **"Save"**

### Option 2: Using Search Bar (KQL Query)
In the search bar at the top, type:
```
kubernetes.container.name: "streamlit-container"
```
Press Enter.

---

## 📝 Step 6: Understanding the Log View

### Log Columns
- **Time** - When the log was generated (@timestamp)
- **_source** - The raw log message (collapsed by default)
- **Document** - Full log details (expand with > arrow)

### Expand a Log Entry
1. Click the **>** arrow on the left of any log entry
2. You'll see all fields:
   - `message` - The actual log message
   - `kubernetes.pod.name` - Pod that generated the log
   - `kubernetes.namespace.name` - Namespace (default)
   - `log` - Full log line
   - `stream` - stdout or stderr

### View Full Message
Click on the **"message"** field value to see the complete log message.

---

## 🧪 Step 7: Test End-to-End

### 7.1 Generate Logs from Streamlit App
1. Open your Streamlit app: `http://<STREAMLIT_LOADBALANCER>`
2. Enter a city: **"Paris"**
3. Enter interests: **"art, food, wine"**
4. Click **"Generate itinerary"**

### 7.2 View Logs in Kibana
1. Go back to Kibana Discover
2. Click the **Refresh** button
3. You should see NEW logs with messages like:
   - `Initialized TravelPlanner instance`
   - `City set successfully`
   - `Interest also set successfully..`
   - `Generating itinerary for Paris and for interests: ['art', 'food', 'wine']`
   - `Itinerary generated successfully..`

### 7.3 Search for Specific Logs
In the search bar, try these queries:

**Search for "Paris":**
```
message: "Paris"
```

**Search for "Generating itinerary":**
```
message: "Generating itinerary"
```

**Search for errors:**
```
message: "error" OR message: "ERROR"
```

---

## 🎨 Step 8: Customize Your View

### Add/Remove Columns
1. On the left panel, hover over field names like `message`, `kubernetes.pod.name`
2. Click the **+** button to add them as columns
3. Click the **-** button to remove them

### Recommended Columns:
- `@timestamp` (always visible)
- `message` (the log content)
- `kubernetes.pod.name` (which pod)
- `log.level` (if available)

### Save Your Search
1. Click **"Save"** at the top
2. Give it a name: "Streamlit App Logs"
3. Click **"Save"**

---

## 🔍 Step 9: Advanced Filtering

### Filter by Log Level (if available)
```
log.level: "INFO"
log.level: "ERROR"
```

### Filter by Pod Name
```
kubernetes.pod.name: "streamlit-app-*"
```

### Exclude Certain Messages
```
NOT message: "health"
```

### Combine Filters
```
kubernetes.container.name: "streamlit-container" AND message: "error"
```

---

## 📊 Step 10: Create Visualizations (Optional)

### Create a Simple Count Visualization
1. Go to **Menu → Visualize Library**
2. Click **"Create visualization"**
3. Select **"Lens"** (recommended for beginners)
4. Select your index pattern: `filebeat-*`
5. Drag `@timestamp` to the horizontal axis
6. Set vertical axis to **Count**
7. Click **"Save"** and name it "Log Count Over Time"

---

## 🛠️ Troubleshooting

### Problem: No Data in Kibana
```bash
# Check if Filebeat is running
kubectl get pods -n logging | grep filebeat

# Check Filebeat logs
kubectl logs -n logging daemonset/filebeat --tail=100

# Verify Logstash is receiving data
kubectl logs -n logging deployment/logstash --tail=50

# Check Elasticsearch health
kubectl exec -n logging deployment/elasticsearch -- curl -X GET "localhost:9200/_cluster/health?pretty"
```

### Problem: Can't Access Kibana on NodePort 30601
```bash
# Verify Kibana is running
kubectl get pods -n logging | grep kibana

# Check Kibana service
kubectl get svc kibana -n logging

# Verify port 30601 is open in security group
aws ec2 describe-security-groups --group-ids <sg-id> --query 'SecurityGroups[*].IpPermissions[*].[FromPort,ToPort]'
```

### Problem: Only Seeing Old Logs
- Adjust the time range to "Last 15 minutes" or "Last 1 hour"
- Click the **Refresh** button
- Generate new logs by using the Streamlit app

### Problem: Too Many Logs (Overwhelming)
Add more filters:
```
kubernetes.container.name: "streamlit-container" AND message: "Generating"
```

---

## 📚 Common Log Queries Reference

### Show all app logs:
```
kubernetes.container.name: "streamlit-container"
```

### Show only errors:
```
kubernetes.container.name: "streamlit-container" AND (message: "error" OR message: "ERROR" OR message: "Failed")
```

### Show successful operations:
```
message: "successfully" OR message: "Success"
```

### Show specific city searches:
```
message: "Generating itinerary for *"
```

### Show logs from last 5 minutes:
Set time range to "Last 5 minutes" using the time picker

---

## ✅ Verification Checklist

- [ ] Can access Kibana UI in browser
- [ ] Index pattern `filebeat-*` created successfully
- [ ] Logs visible in Discover view
- [ ] Can filter logs by container name
- [ ] Generated test logs from Streamlit app
- [ ] See application logs in Kibana
- [ ] Can search for specific messages
- [ ] Time range selector works correctly
- [ ] Can expand and view full log details

---

## 🎓 Next Steps

1. **Set up Alerts**: Configure Kibana alerts for errors
2. **Create Dashboards**: Build custom dashboards for monitoring
3. **Log Retention**: Configure Elasticsearch index lifecycle policies
4. **Export Logs**: Export specific logs for analysis
5. **Add More Filters**: Create saved searches for common queries

---

## 📞 Support Commands

### Get all logging components status:
```bash
kubectl get all -n logging
```

### Check disk usage (Elasticsearch):
```bash
kubectl exec -n logging deployment/elasticsearch -- df -h
```

### View Elasticsearch indices:
```bash
kubectl exec -n logging deployment/elasticsearch -- curl -X GET "localhost:9200/_cat/indices?v"
```

### Delete old indices (if needed):
```bash
kubectl exec -n logging deployment/elasticsearch -- curl -X DELETE "localhost:9200/filebeat-2026.02.01"
```

---

## 🎉 Success!

You should now be able to:
- Access Kibana dashboard
- View container logs in real-time
- Filter logs for your Streamlit app
- Search for specific log messages
- Monitor application behavior

Happy logging! 🚀
