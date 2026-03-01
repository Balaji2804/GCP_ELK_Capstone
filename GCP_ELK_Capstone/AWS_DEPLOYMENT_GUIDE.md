# AWS EKS Deployment Guide - AI Travel Agent with ELK Stack

## Architecture Overview

- **Streamlit App**: Runs on port 8501, exposed via LoadBalancer on port 80
- **Elasticsearch**: Stores logs on port 9200 (ClusterIP - internal only)
- **Kibana**: Web UI on port 5601, exposed via NodePort 30601
- **Logstash**: Receives logs from Filebeat on port 5044
- **Filebeat**: DaemonSet collecting container logs from all nodes

---

## Prerequisites

- AWS Account with appropriate IAM permissions
- Docker installed (will be installed on EC2)
- kubectl installed (will be installed on EC2)
- eksctl installed (will be installed on EC2)
- Your GROQ API Key

---

## Step 1: Create IAM Role and Launch EC2 Instance (Management Node)

### 1.1 Create IAM Role for EC2

**Via AWS Console:**
1. Go to **IAM Console** → **Roles** → **Create role**
2. Select **AWS service** → **EC2** → **Next**
3. Attach the following policies:
   - `AmazonEC2ContainerRegistryFullAccess` (for ECR)
   - `AmazonEKSClusterPolicy` (for EKS management)
   - `IAMFullAccess` (for eksctl to create roles)
   - `AmazonVPCFullAccess` (for eksctl to create VPC resources)
   - `CloudFormationFullAccess` (eksctl uses CloudFormation)
4. Name the role: `EC2-EKS-Management-Role`
5. Click **Create role**

**Via AWS CLI (Alternative):**
```bash
# Create a trust policy file
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the IAM role
aws iam create-role \
  --role-name EC2-EKS-Management-Role \
  --assume-role-policy-document file://trust-policy.json

# Attach necessary policies
aws iam attach-role-policy \
  --role-name EC2-EKS-Management-Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess

aws iam attach-role-policy \
  --role-name EC2-EKS-Management-Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy

aws iam attach-role-policy \
  --role-name EC2-EKS-Management-Role \
  --policy-arn arn:aws:iam::aws:policy/IAMFullAccess

aws iam attach-role-policy \
  --role-name EC2-EKS-Management-Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonVPCFullAccess

aws iam attach-role-policy \
  --role-name EC2-EKS-Management-Role \
  --policy-arn arn:aws:iam::aws:policy/CloudFormationFullAccess

# Create instance profile and add role
aws iam create-instance-profile \
  --instance-profile-name EC2-EKS-Management-Profile

aws iam add-role-to-instance-profile \
  --instance-profile-name EC2-EKS-Management-Profile \
  --role-name EC2-EKS-Management-Role
```

### 1.2 Create EC2 Instance with IAM Role

**Via AWS Console:**
1. Go to **EC2 Console** → **Launch Instance**
2. Configure:
   - **Name**: AI-Travel-Agent-Management
   - **AMI**: Ubuntu 22.04 LTS or Amazon Linux 2023
   - **Instance Type**: t3.medium or larger
   - **Key pair**: Select or create a key pair for SSH access
   - **IAM instance profile**: Select `EC2-EKS-Management-Role`
   - **Security Group**: 
     - Allow SSH (22) from your IP
     - Allow Custom TCP (5601) from your IP (for Kibana access later)
3. Click **Launch Instance**

**Via AWS CLI (Alternative):**
```bash
# Replace with your key pair name and security group ID
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.medium \
  --key-name your-key-pair \
  --security-group-ids sg-xxxxxxxxx \
  --iam-instance-profile Name=EC2-EKS-Management-Profile \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=AI-Travel-Agent-Management}]'
```

### 1.3 Connect to EC2 and Verify IAM Role

```bash
# SSH into your EC2 instance
ssh -i your-key-pair.pem ec2-user@<EC2_PUBLIC_IP>  # Amazon Linux
# OR
ssh -i your-key-pair.pem ubuntu@<EC2_PUBLIC_IP>  # Ubuntu

# Verify IAM role is attached and working
aws sts get-caller-identity
# Should show your account ID and role without requiring credentials
```

### 1.4 Install Required Tools on EC2

```bash
# Update system
sudo yum update -y  # Amazon Linux
# OR
sudo apt update && sudo apt upgrade -y  # Ubuntu

# Install Docker
sudo yum install -y docker  # Amazon Linux
# OR
sudo apt install -y docker.io  # Ubuntu

sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Install kubectl
curl -LO "https://dl.k8s.io/release/v1.28.0/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# Install eksctl
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin/

# Install git
sudo yum install -y git  # Amazon Linux
# OR
sudo apt install -y git  # Ubuntu

# Log out and back in for Docker group changes to take effect
```

### 1.5 Configure AWS CLI Default Region (No Credentials Needed)
```bash
# Set default region only - IAM role provides authentication automatically
aws configure set region us-east-1
aws configure set output json

# Verify AWS access works with IAM role
aws sts get-caller-identity
# Should display your account ID, user/role ARN without requiring access keys

# Test permissions
# Attach the following inline policy to your EC2 IAM role to allow all required EKS operations:
#
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eks:ListClusters",
        "eks:DescribeCluster",
        "eks:CreateCluster",
        "eks:DeleteCluster",
        "eks:UpdateClusterConfig",
        "eks:UpdateClusterVersion",
        "eks:ListNodegroups",
        "eks:DescribeNodegroup",
        "eks:CreateNodegroup",
        "eks:UpdateNodegroupConfig",
        "eks:UpdateNodegroupVersion",
        "eks:DeleteNodegroup",
        "eks:AccessKubernetesApi",
        "eks:TagResource",
        "eks:UntagResource",
        "eks:ListUpdates",
        "eks:DescribeUpdate"
      ],
      "Resource": "*"
    }
  ]
}
aws eks list-clusters
aws ecr describe-repositories
```

# Note: If you use eksctl, you must also add the following action to your inline policy's Action list above:
#         "eks:DescribeClusterVersions"
# This is required for eksctl to query available EKS versions during cluster creation.

### 1.6 Note on eksctl Cluster Creation

If you use eksctl, you must also add the following action to your inline policy:
   "eks:DescribeClusterVersions"
Example (add to the Action list above):
         "eks:DescribeClusterVersions"
#
# This is required for eksctl to query available EKS versions during cluster creation.

---

## Step 2: Create EKS Cluster

**Note:** If you encounter SCP (Service Control Policy) errors with eksctl, use the **Manual AWS Console Method** below.

### Method A: Create Cluster with eksctl (Quick Method)

**Note:** This may fail if your AWS Organization has SCPs that block `eks:DescribeClusterVersions`.

```bash
# This creates a cluster with 2 t3.medium nodes
eksctl create cluster \
  --name ai-travel-agent \
  --region us-east-1 \
  --node-type t3.medium \
  --nodes 2 \
  --nodes-min 2 \
  --nodes-max 4 \
  --managed

# This takes 15-20 minutes to complete
```

If you get **AccessDeniedException** with "explicit deny in a service control policy", proceed with **Method B** below.

---

### Method B: Create Cluster via AWS Console (Alternative - Bypasses SCP Issues)

#### 2.1 Create EKS Cluster IAM Role

**Via AWS Console:**
1. Go to **IAM Console** → **Roles** → **Create role**
2. Select **AWS service** → **EKS** → **EKS - Cluster** → **Next**
3. The policy **AmazonEKSClusterPolicy** is automatically attached
4. Name the role: `EKS-Cluster-Role`
5. Click **Create role**

**Via AWS CLI (Alternative):**
```bash
# Create trust policy for EKS
cat > eks-cluster-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "eks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the role
aws iam create-role \
  --role-name EKS-Cluster-Role \
  --assume-role-policy-document file://eks-cluster-trust-policy.json

# Attach required policy
aws iam attach-role-policy \
  --role-name EKS-Cluster-Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy
```

#### 2.2 Create EKS Node Group IAM Role

**Via AWS Console:**
1. Go to **IAM Console** → **Roles** → **Create role**
2. Select **AWS service** → **EC2** → **Next**
3. Attach the following policies:
   - `AmazonEKSWorkerNodePolicy`
   - `AmazonEKS_CNI_Policy`
   - `AmazonEC2ContainerRegistryReadOnly`
4. Name the role: `EKS-NodeGroup-Role`
5. Click **Create role**

**Via AWS CLI (Alternative):**
```bash
# Create trust policy for EC2
cat > eks-nodegroup-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the role
aws iam create-role \
  --role-name EKS-NodeGroup-Role \
  --assume-role-policy-document file://eks-nodegroup-trust-policy.json

# Attach required policies
aws iam attach-role-policy \
  --role-name EKS-NodeGroup-Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy

aws iam attach-role-policy \
  --role-name EKS-NodeGroup-Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy

aws iam attach-role-policy \
  --role-name EKS-NodeGroup-Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
```

#### 2.3 Create EKS Cluster via AWS Console

1. **Navigate to EKS Console:**
   - Go to AWS Console → Search for **EKS** → **Amazon EKS** → **Clusters**
   - Click **Create cluster** (or **Add cluster** → **Create**)

2. **Configure Cluster (Step 1):**
   - **Name**: `ai-travel-agent`
   - **Kubernetes version**: `1.28` (or latest available)
   - **Cluster service role**: Select `EKS-Cluster-Role` (created in 2.1)
   - Click **Next**

3. **Specify Networking (Step 2):**
   - **VPC**: Select your default VPC (or create a new one)
   - **Subnets**: Select at least 2 subnets in different availability zones
   - **Security groups**: Leave default (EKS creates one automatically)
   - **Cluster endpoint access**: 
     - Select **Public** (or **Public and private** for production)
   - Click **Next**

4. **Configure Observability (Step 3):**
   - Leave all logging options **unchecked** for now (to reduce costs)
   - Click **Next**

5. **Select Add-ons (Step 4):**
   - Keep the default add-ons:
     - Amazon VPC CNI
     - kube-proxy
     - CoreDNS
   - Click **Next**

6. **Review and Create (Step 5):**
   - Review all settings
   - Click **Create**
   - **Cluster creation takes 10-15 minutes**

7. **Wait for Cluster to be Active:**
   - Status will change from **Creating** → **Active**
   - You can proceed to the next step while waiting

#### 2.4 Create Node Group via AWS Console

**Wait until the cluster status is "Active" before proceeding.**

1. **Navigate to Your Cluster:**
   - Go to **EKS Console** → **Clusters** → Click **ai-travel-agent**

2. **Go to Compute Tab:**
   - Click the **Compute** tab
   - Under **Node groups**, click **Add node group**

3. **Configure Node Group (Step 1):**
   - **Name**: `ng-1`
   - **Node IAM role**: Select `EKS-NodeGroup-Role` (created in 2.2)
   - Click **Next**

4. **Set Compute and Scaling Configuration (Step 2):**
   - **AMI type**: Amazon Linux 2 (AL2_x86_64)
   - **Capacity type**: On-Demand
   - **Instance types**: Remove default, add **t3.medium**
   - **Disk size**: 20 GiB
   - **Scaling configuration**:
     - Desired size: **2**
     - Minimum size: **2**
     - Maximum size: **4**
   - Click **Next**

5. **Specify Networking (Step 3):**
   - **Subnets**: Select the same subnets as the cluster (should be pre-selected)
   - **Configure remote access to nodes**: 
     - Enable (optional, for SSH access)
     - Select your EC2 key pair if you want SSH access
   - Click **Next**

6. **Review and Create:**
   - Review settings
   - Click **Create**
   - **Node group creation takes 3-5 minutes**

#### 2.5 Configure kubectl to Access the Cluster

Once both the cluster and node group are **Active**, configure kubectl on your EC2 instance.

**Method 1: Using AWS CLI (Standard - May Fail with SCP)**

```bash
# Update kubeconfig to connect to the new cluster
aws eks update-kubeconfig \
  --region us-east-1 \
  --name ai-travel-agent

# Verify connection
kubectl get nodes
# Should show 2 nodes in Ready state

kubectl cluster-info
# Should show cluster endpoint
```

**If you get AccessDeniedException with SCP error, use Method 2 below.**

---

**Method 2: Manual kubectl Configuration (Bypasses SCP for DescribeCluster)**

If the AWS CLI command fails due to SCP restrictions, manually configure kubectl:

**Step 1: Get Cluster Information from AWS Console**

1. Go to **AWS Console** → **EKS** → **Clusters** → Click **ai-travel-agent**
2. In the **Overview** tab, copy the following:
   - **API server endpoint** (e.g., `https://XXXXX.gr7.us-east-1.eks.amazonaws.com`)
   - **Certificate authority** (click "Download" or copy the base64 data)

**Step 2: Get Certificate Authority Data**

In the AWS Console EKS cluster page:
1. Scroll down to **Cluster configuration**
2. Find **Certificate authority**
3. Click **Download** to get the certificate, or copy the displayed base64-encoded certificate data

**Step 3: Create kubeconfig File Manually**

On your EC2 instance, create or edit `~/.kube/config`:

```bash
# Create .kube directory if it doesn't exist
mkdir -p ~/.kube

# Create/edit the kubeconfig file
cat > ~/.kube/config << 'EOF'
apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: REPLACE_WITH_YOUR_CERTIFICATE_DATA
    server: REPLACE_WITH_YOUR_API_SERVER_ENDPOINT
  name: ai-travel-agent
contexts:
- context:
    cluster: ai-travel-agent
    user: ai-travel-agent
  name: ai-travel-agent
current-context: ai-travel-agent
kind: Config
preferences: {}
users:
- name: ai-travel-agent
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      args:
      - --region
      - us-east-1
      - eks
      - get-token
      - --cluster-name
      - ai-travel-agent
      command: aws
      env: null
      interactiveMode: IfAvailable
      provideClusterInfo: false
EOF

# Set proper permissions
chmod 600 ~/.kube/config
```

**Step 4: Replace Placeholders**

Edit the file and replace:

1. `REPLACE_WITH_YOUR_CERTIFICATE_DATA` - Paste the base64 certificate data copied from AWS Console (single line, no line breaks)
2. `REPLACE_WITH_YOUR_API_SERVER_ENDPOINT` - Paste the API server endpoint URL

**Quick edit command:**
```bash
nano ~/.kube/config
# Or use vi:
vi ~/.kube/config
```

**Example of what it should look like:**
```yaml
apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSURCVENDQWUyZ0F3SUJBZ0lJZHpFd...
    server: https://A1B2C3D4E5F6.gr7.us-east-1.eks.amazonaws.com
  name: ai-travel-agent
# ... rest of config
```

**Step 5: Verify kubectl Configuration**

```bash
# Test kubectl connection
kubectl get nodes

# Should show:
# NAME                             STATUS   ROLES    AGE   VERSION
# ip-xxx-xxx-xxx-xxx.ec2.internal   Ready    <none>   5m    v1.28.x
# ip-xxx-xxx-xxx-xxx.ec2.internal   Ready    <none>   5m    v1.28.x

# Check cluster info
kubectl cluster-info

# Check system pods
kubectl get pods -n kube-system
```

If you still get errors, verify:
- The certificate data is on a **single line** with no line breaks
- The API server endpoint is correct (starts with `https://`)
- Your EC2 IAM role has `sts:AssumeRole` permissions (for aws-iam-authenticator)

---

#### 2.6 Create Logging Namespace
```bash
kubectl create namespace logging
```

---

### Verify Cluster (Both Methods)

After cluster creation (either method), verify everything is working:

```bash
# Check nodes are ready
kubectl get nodes
# NAME                             STATUS   ROLES    AGE   VERSION
# ip-xxx-xxx-xxx-xxx.ec2.internal   Ready    <none>   2m    v1.28.x
# ip-xxx-xxx-xxx-xxx.ec2.internal   Ready    <none>   2m    v1.28.x

# Check cluster info
kubectl cluster-info

# Check system pods
kubectl get pods -n kube-system
# All pods should be Running

# Check namespaces
kubectl get namespaces
```

**Note about Node Groups:**

If you see nodes in `Ready` state (even without a managed node group in the AWS Console), you can proceed with the deployment. The node group is just an AWS management construct - what matters is that nodes are joined to the cluster and running.

Example of working nodes (may show instance IDs instead of DNS names):
```
NAME                  STATUS   ROLES    AGE   VERSION
i-02783f5c0498c079a   Ready    <none>   7h    v1.35.0-eks-xxx
i-0eb831301f7c53a37   Ready    <none>   7h    v1.35.0-eks-xxx
```

As long as `STATUS = Ready`, you can deploy workloads. Continue to the next step.

---

### Install Amazon EBS CSI Driver (Required for Elasticsearch PersistentVolume)

**IMPORTANT:** EKS clusters require the EBS CSI driver to provision EBS volumes for PersistentVolumeClaims. Without this, Elasticsearch pods will remain in "Pending" state.

#### Option A: Install via AWS Console (Easiest)

1. Go to **AWS Console** → **EKS** → **Clusters** → **ai-travel-agent**
2. Click the **Add-ons** tab
3. Click **Get more add-ons**
4. Find and select **Amazon EBS CSI Driver**
5. Click **Next**
6. Keep default version (latest)
7. Click **Next** → **Create**
8. Wait 2-3 minutes for installation to complete

#### Option B: Install via kubectl

```bash
# Add the Amazon EBS CSI driver
kubectl apply -k "github.com/kubernetes-sigs/aws-ebs-csi-driver/deploy/kubernetes/overlays/stable/?ref=release-1.28"

# Verify the driver is installed
kubectl get pods -n kube-system | grep ebs-csi

# Should show ebs-csi-controller and ebs-csi-node pods running
```

#### Option C: Install via eksctl (if you used eksctl to create cluster)

```bash
eksctl create addon \
  --name aws-ebs-csi-driver \
  --cluster ai-travel-agent \
  --region us-east-1
```

#### Create IAM Role for EBS CSI Driver

The EBS CSI driver needs IAM permissions to create and manage EBS volumes. You must create an IAM role with the proper trust policy and attach it to the add-on.

**Method 1: Via AWS Console (Recommended - Easiest)**

**Step 1: Enable OIDC Provider for Your Cluster (One-time setup)**

1. Go to **EKS Console** → **Clusters** → **ai-travel-agent** → **Overview** tab
2. Under **Cluster configuration**, find **OpenID Connect provider URL**
3. Copy the OIDC provider URL (e.g., `https://oidc.eks.us-east-1.amazonaws.com/id/XXXXX`)
4. Go to **IAM Console** → **Identity providers**
5. If provider doesn't exist:
   - Click **Add provider**
   - Provider type: **OpenID Connect**
   - Provider URL: Paste the OIDC URL from step 3
   - Audience: `sts.amazonaws.com`
   - Click **Add provider**

**Step 2: Create IAM Role for EBS CSI Driver**

1. Go to **IAM Console** → **Roles** → **Create role**

2. **Select trusted entity:**
   - Trusted entity type: **Web identity**
   - Identity provider: Select your cluster's OIDC provider
   - Audience: `sts.amazonaws.com`
   - Click **Next**

3. **Add permissions:**
   - Search for: `AmazonEBSCSIDriverPolicy`
   - Select the checkbox for **AmazonEBSCSIDriverPolicy** (AWS managed policy)
   - Click **Next**

4. **Name the role:**
   - Role name: `AmazonEKS_EBS_CSI_DriverRole`
   - Description: `IAM role for EBS CSI Driver on ai-travel-agent cluster`
   - Click **Create role**

5. **Edit Trust Policy (IMPORTANT):**
   - Find and click on your newly created role: `AmazonEKS_EBS_CSI_DriverRole`
   - Click the **Trust relationships** tab
   - Click **Edit trust policy**
   - Replace the entire trust policy with this (replace `<AWS_ACCOUNT_ID>` and `<OIDC_ID>` with your values):

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": {
           "Federated": "arn:aws:iam::<AWS_ACCOUNT_ID>:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/<OIDC_ID>"
         },
         "Action": "sts:AssumeRoleWithWebIdentity",
         "Condition": {
           "StringEquals": {
             "oidc.eks.us-east-1.amazonaws.com/id/<OIDC_ID>:aud": "sts.amazonaws.com",
             "oidc.eks.us-east-1.amazonaws.com/id/<OIDC_ID>:sub": "system:serviceaccount:kube-system:ebs-csi-controller-sa"
           }
         }
       }
     ]
   }
   ```

   **How to get the values:**
   - `<AWS_ACCOUNT_ID>`: Your AWS account ID (e.g., `201983195686`)
   - `<OIDC_ID>`: From EKS cluster Overview page, copy the last part of OIDC URL
     - Example: If OIDC URL is `https://oidc.eks.us-east-1.amazonaws.com/id/5EB4245A0FA5AF1A52DED225E0F26411`
     - Then OIDC_ID is: `5EB4245A0FA5AF1A52DED225E0F26411`

   - Click **Update policy**

6. **Copy the Role ARN:**
   - In the role summary page, copy the **ARN** (e.g., `arn:aws:iam::201983195686:role/AmazonEKS_EBS_CSI_DriverRole`)

**Step 3: Attach IAM Role to EBS CSI Add-on**

1. Go to **EKS Console** → **Clusters** → **ai-travel-agent** → **Add-ons** tab
2. Click on **Amazon EBS CSI Driver**
3. Click **Edit**
4. Under **IAM role**, select **Use an existing role**
5. In the **Role ARN** field, paste the ARN you copied in Step 2.6
6. Click **Save changes**
7. Wait 1-2 minutes for changes to apply

---

**Method 2: Quick Console Method (If automatic creation works)**

1. Go to **EKS Console** → **Clusters** → **ai-travel-agent** → **Add-ons** tab
2. Click on **Amazon EBS CSI Driver**
3. Click **Edit**
4. Under **IAM role**, click **Create new IAM role**
5. Follow the prompts - AWS will create the role automatically
6. Click **Save changes**

**Note:** This automatic method may fail if OIDC provider is not configured. Use Method 1 if this doesn't work.

---

**Method 3: Via AWS CLI**
```bash
# Get your cluster's OIDC provider
export CLUSTER_NAME=ai-travel-agent
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Get OIDC provider URL (may require eks:DescribeCluster permission - might fail with SCP)
OIDC_PROVIDER=$(aws eks describe-cluster --name $CLUSTER_NAME --region $AWS_REGION --query "cluster.identity.oidc.issuer" --output text | sed -e "s/^https:\/\///")

# If the above fails due to SCP, use Method 1 (Console) instead

# Create IAM trust policy
cat > ebs-csi-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/${OIDC_PROVIDER}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "${OIDC_PROVIDER}:aud": "sts.amazonaws.com",
          "${OIDC_PROVIDER}:sub": "system:serviceaccount:kube-system:ebs-csi-controller-sa"
        }
      }
    }
  ]
}
EOF

# Create the IAM role
aws iam create-role \
  --role-name AmazonEKS_EBS_CSI_DriverRole \
  --assume-role-policy-document file://ebs-csi-trust-policy.json

# Attach the AWS managed policy
aws iam attach-role-policy \
  --role-name AmazonEKS_EBS_CSI_DriverRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy

# Annotate the service account
kubectl annotate serviceaccount ebs-csi-controller-sa \
  -n kube-system \
  eks.amazonaws.com/role-arn=arn:aws:iam::${AWS_ACCOUNT_ID}:role/AmazonEKS_EBS_CSI_DriverRole
```

#### Verify EBS CSI Driver

```bash
# Check if CSI driver pods are running
kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-ebs-csi-driver

# Should show:
# ebs-csi-controller-xxx   (should be Running)
# ebs-csi-node-xxx         (should be Running on each node)

# Check if StorageClass exists
kubectl get storageclass

# Should show gp2 or gp3 StorageClass
```

---

#### Troubleshooting: Cannot Create OIDC Provider (Permissions Issue)

**Error:**
```
User is not authorized to perform: iam:CreateOpenIDConnectProvider because no permissions boundary allows the iam:CreateOpenIDConnectProvider action
```

**Cause:** Your IAM user/role doesn't have permission to create OIDC providers. This is common in sandbox or restricted AWS accounts.

**Workaround: Use Node IAM Role Instead (No OIDC Required)**

Instead of using IRSA (IAM Roles for Service Accounts), you can grant EBS CSI permissions directly to your **Node Group IAM Role**. This is less secure but works when OIDC is not available.

**Step 1: Identify Your Node Group IAM Role**

```bash
# Get the node group IAM role name
aws eks describe-nodegroup \
  --cluster-name ai-travel-agent \
  --nodegroup-name ng-1 \
  --region us-east-1 \
  --query 'nodegroup.nodeRole' \
  --output text

# Or check via console:
# EKS → Clusters → ai-travel-agent → Compute → ng-1 → Node IAM role ARN
```

From your setup, this should be: `EKS-NodeGroup-Role`

**Step 2: Attach EBS CSI Policy to Node Role via Console**

1. Go to **IAM Console** → **Roles**
2. Search for: `EKS-NodeGroup-Role` (or your node group role name)
3. Click on the role
4. Click **Add permissions** → **Attach policies**
5. Search for: `AmazonEBSCSIDriverPolicy`
6. Select the checkbox for **AmazonEBSCSIDriverPolicy**
7. Click **Add permissions**

**Step 3: Remove Service Account Annotation (Optional)**

```bash
# If you previously tried to annotate the service account, remove it
kubectl annotate serviceaccount ebs-csi-controller-sa \
  -n kube-system \
  eks.amazonaws.com/role-arn- 

# Note: The hyphen at the end removes the annotation
```

**Step 4: Restart EBS CSI Driver Pods**

```bash
# Restart the CSI controller to pick up node role permissions
kubectl rollout restart deployment ebs-csi-controller -n kube-system

# Wait for pods to restart
kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-ebs-csi-driver -w
```

**Step 5: Verify It Works**

```bash
# Check if the EBS CSI driver can now provision volumes
kubectl get storageclass

# Deploy Elasticsearch to test
kubectl apply -f elasticsearch.yaml

# Watch the pod start
kubectl get pods -n logging -w

# Check PVC is bound
kubectl get pvc -n logging
# Should show: elasticsearch-pvc   Bound
```

**Alternative: Ask Your AWS Administrator**

If you need proper IRSA setup, contact your AWS organization administrator to:

1. **Create the OIDC Provider:**
   - Go to **IAM Console** → **Identity providers** → **Add provider**
   - Provider type: **OpenID Connect**
   - Provider URL: `https://oidc.eks.ap-south-1.amazonaws.com/id/5EB4245A0FA5AF1A52DED225E0F26411`
   - Audience: `sts.amazonaws.com`

2. **Then continue with Method 1** to create the IAM role and attach it to the EBS CSI add-on

**Note:** The node role approach grants EBS permissions to ALL pods running on the nodes, not just the EBS CSI driver. For production, use IRSA (requires OIDC provider). For testing/sandbox, the node role approach is acceptable.

---

#### Troubleshooting: EBS CSI Add-on Stuck in "Creating" State

**Symptoms:**
- Add-on status shows "Creating" for more than 5 minutes
- "IAM role for service account (IRSA): Not set" in add-on details
- CSI driver pods not appearing in `kube-system` namespace

**Cause:** The add-on is waiting for IAM role configuration, which requires OIDC provider (that you can't create).

**Solution: Delete Add-on and Use Node Role Approach**

**Step 1: Delete the Stuck Add-on**

1. Go to **AWS Console** → **EKS** → **Clusters** → **ai-travel-agent** → **Add-ons** tab
2. Select **Amazon EBS CSI Driver**
3. Click **Remove**
4. Choose **Preserve on cluster** (if asked, but add-on likely hasn't deployed anything yet)
5. Confirm removal

**Step 2: Attach EBS Policy to Node IAM Role**

1. Go to **IAM Console** → **Roles**
2. Search and click: `EKS-NodeGroup-Role`
3. Click **Add permissions** → **Attach policies**
4. Search for: `AmazonEBSCSIDriverPolicy`
5. Select the checkbox
6. Click **Add permissions**

**Step 3: Deploy CSI Driver Manually (Bypasses Add-on System)**

```bash
# Deploy EBS CSI driver directly via kubectl
kubectl apply -k "github.com/kubernetes-sigs/aws-ebs-csi-driver/deploy/kubernetes/overlays/stable/?ref=release-1.35"

# Wait for pods to start (uses node role permissions automatically)
kubectl get pods -n kube-system | grep ebs-csi

# Should show within 2-3 minutes:
# ebs-csi-controller-xxx    Running
# ebs-csi-node-xxx          Running (on each node)
```

**Step 4: Verify CSI Driver Works**

```bash
# Check StorageClass exists
kubectl get storageclass
# Should show: gp2 or gp3

# Test by creating PVC (deploy Elasticsearch)
kubectl apply -f elasticsearch.yaml

# Watch PVC get bound
kubectl get pvc -n logging -w
# Should show: elasticsearch-pvc   Pending → Bound (within 1-2 min)
```

**Why This Works:**

The manually deployed CSI driver inherits IAM permissions from the node role (since we attached `AmazonEBSCSIDriverPolicy` to it). It doesn't need IRSA/OIDC provider.

**Alternative: Wait for AWS Admin to Create OIDC Provider**

If you need to use the add-on approach:
1. Ask AWS admin to create OIDC provider (see earlier troubleshooting section)
2. Create IAM role following Method 1 (Console approach)
3. Edit the add-on and select the IAM role
4. Add-on will complete creation

**Note:** The node role approach grants EBS permissions to ALL pods running on the nodes, not just the EBS CSI driver. For production, use IRSA (requires OIDC provider). For testing/sandbox, the node role approach is acceptable.

---

## Step 3: Build and Push Docker Image to ECR

### 3.1 Clone Your Repository (if not already on EC2)
```bash
git clone <your-repo-url>
cd AI_Travel_Agent
```

### 3.2 Create ECR Repository
```bash
aws ecr create-repository \
  --repository-name streamlit-app \
  --region us-east-1
```

### 3.3 Authenticate Docker to ECR
```bash
# Get your AWS Account ID
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=us-east-1

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
```

### 3.4 Build and Push Docker Image
```bash
# Build the image
docker build -t streamlit-app:latest .

# Tag the image
docker tag streamlit-app:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/streamlit-app:latest

# Push to ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/streamlit-app:latest
```

### 3.5 Update k8s-deployment.yaml
```bash
# Replace the image URL in k8s-deployment.yaml with your ECR URL
sed -i "s|<AWS_ACCOUNT_ID>|$AWS_ACCOUNT_ID|g" k8s-deployment.yaml
sed -i "s|<REGION>|$AWS_REGION|g" k8s-deployment.yaml

# Verify the change
grep "image:" k8s-deployment.yaml
```

---

## Step 4: Create Kubernetes Secrets

### 4.1 Create Secret for GROQ API Key
```bash
# Create secret in default namespace (for the app)
kubectl create secret generic llmops-secrets \
  --from-literal=GROQ_API_KEY=your_actual_groq_api_key_here

# Verify secret
kubectl get secrets
```

---

## Step 5: Deploy ELK Stack

**⚠️ IMPORTANT: All deployments require tolerations for EKS Auto Mode nodes**

Your cluster uses Auto Mode with `CriticalAddonsOnly:NoSchedule` taints. All deployment YAMLs have been updated with the required tolerations.

### 5.1 Deploy Elasticsearch

**Storage Configuration:**
- Using **emptyDir** (non-persistent storage)
- Suitable for demos and testing
- Data persists across container restarts
- Data is lost if pod is deleted/rescheduled

**Deploy Elasticsearch:**
```bash
kubectl apply -f elasticsearch.yaml

# Wait for Elasticsearch to be ready (takes 1-2 minutes with emptyDir)
kubectl get pods -n logging -w
# Press Ctrl+C once elasticsearch pod shows 1/1 Running

# Verify Elasticsearch is healthy
kubectl exec -n logging deployment/elasticsearch -- curl -X GET "localhost:9200/_cluster/health?pretty"

# Check logs if pod doesn't start
kubectl logs -n logging deployment/elasticsearch --tail=50
```

### 5.2 Deploy Logstash
```bash
kubectl apply -f logstash.yaml

# Wait for Logstash to be ready
kubectl get pods -n logging | grep logstash
```

### 5.3 Deploy Filebeat
```bash
kubectl apply -f filebeat.yaml

# Verify Filebeat DaemonSet is running on all nodes
kubectl get daemonset -n logging
kubectl get pods -n logging | grep filebeat
```

### 5.4 Deploy Kibana
```bash
kubectl apply -f kibana.yaml

# Wait for Kibana to be ready (takes 2-3 minutes)
kubectl get pods -n logging | grep kibana
```

---

## Step 6: Deploy Streamlit Application

```bash
kubectl apply -f k8s-deployment.yaml

# Wait for the app to be ready
kubectl get pods -l app=streamlit
kubectl get svc streamlit-service
```

---

## Step 7: Access the Applications

### 7.1 Access Streamlit App via LoadBalancer

```bash
# Get LoadBalancer URL (takes 2-3 minutes to provision)
kubectl get svc streamlit-service

# Copy the EXTERNAL-IP shown (e.g., a1234567890.us-east-1.elb.amazonaws.com)
# Access the app at: http://<EXTERNAL-IP>
```

### 7.2 Access Kibana via NodePort

**Option A: Using Node Public IP + NodePort**
```bash
# Get the public IP of any EKS worker node
kubectl get nodes -o wide

# Find the EXTERNAL-IP of any node
# Access Kibana at: http://<NODE_EXTERNAL_IP>:30601
```

**Option B: Using kubectl port-forward (Recommended)**
```bash
# Port forward from your EC2 instance to Kibana
kubectl port-forward -n logging svc/kibana 5601:5601 --address 0.0.0.0

# Now access Kibana from your local machine:
# 1. Add inbound rule to EC2 security group: Allow TCP 5601 from your IP
# 2. Access Kibana at: http://<EC2_PUBLIC_IP>:5601
```

**Option C: Using LoadBalancer for Kibana (Alternative)**
```bash
# Edit kibana.yaml service type from NodePort to LoadBalancer
kubectl patch svc kibana -n logging -p '{"spec":{"type":"LoadBalancer"}}'

# Get the LoadBalancer URL
kubectl get svc kibana -n logging
```

---

## Step 8: Configure Kibana to View Logs

### 8.1 Initial Kibana Setup
1. Open Kibana in your browser: `http://<KIBANA_URL>:5601` or `http://<NODE_IP>:30601`
2. Click **"Explore on my own"**
3. Go to **Management** → **Stack Management** (gear icon in bottom left)
4. Click **Index Patterns** under Kibana section

### 8.2 Create Index Pattern
1. Click **"Create index pattern"**
2. Enter index pattern: `filebeat-*`
3. Click **"Next step"**
4. Select **@timestamp** as the Time field
5. Click **"Create index pattern"**

### 8.3 View Logs in Discover
1. Click the **hamburger menu** → **Discover**
2. Select **filebeat-*** index pattern from the dropdown
3. Set time range (top right): **Last 15 minutes** or **Today**
4. You should see logs from all containers in your cluster

### 8.4 Filter Streamlit App Logs
Add filters to view only your app's logs:
- Click **"Add filter"**
- Field: `kubernetes.container.name`
- Operator: `is`
- Value: `streamlit-container`
- Click **"Save"**

---

## Step 9: Test the Application

### 9.1 Test Streamlit App
1. Navigate to `http://<STREAMLIT_LOADBALANCER_URL>`
2. Enter a city name: **New York**
3. Enter interests: **museums, food, parks**
4. Click **"Generate itinerary"**
5. Verify the AI generates an itinerary

### 9.2 Verify Logs in Kibana
1. Go back to Kibana Discover
2. Refresh the page
3. Search for: `Generating itinerary` or `city`
4. You should see logs from your travel planner application

---

## Port Summary

| Component | Port | Type | Access |
|-----------|------|------|--------|
| Streamlit App | 8501 | ContainerPort | Internal |
| Streamlit Service | 80 → 8501 | LoadBalancer | External via ELB |
| Elasticsearch | 9200 | ClusterIP | Internal only |
| Kibana | 5601 | NodePort 30601 | External via Node IP |
| Logstash | 5044 | ClusterIP | Internal (Filebeat) |
| Logstash Monitoring | 9600 | ClusterIP | Internal |

---

## Troubleshooting

### Check Pod Status
```bash
# Check all pods
kubectl get pods --all-namespaces

# Check app pods
kubectl get pods -l app=streamlit

# Check ELK pods
kubectl get pods -n logging

# Describe a specific pod for details
kubectl describe pod <pod-name> -n <namespace>
```

### View Pod Logs
```bash
# View Streamlit app logs
kubectl logs -l app=streamlit --tail=100

# View Elasticsearch logs
kubectl logs -n logging deployment/elasticsearch --tail=100

# View Kibana logs
kubectl logs -n logging deployment/kibana --tail=100

# View Filebeat logs
kubectl logs -n logging daemonset/filebeat --tail=50
```

### Check Services
```bash
# Check all services
kubectl get svc --all-namespaces

# Get LoadBalancer external URL
kubectl get svc streamlit-service
```

### Test Elasticsearch
```bash
# Port forward to test Elasticsearch directly
kubectl port-forward -n logging svc/elasticsearch 9200:9200

# In another terminal, test the connection
curl http://localhost:9200/_cluster/health?pretty
```

### Common Issues

**⚠️ EKS Auto Mode Cluster Requirements**

If your cluster uses EKS Auto Mode (compute nodes with `CriticalAddonsOnly` taint), ensure:
- ✅ All pod specs include tolerations for `CriticalAddonsOnly:NoSchedule`
- ✅ Use emptyDir storage (not EBS volumes)
- ✅ IAM permissions work via node roles (not IRSA/OIDC)

All deployment YAMLs in this project have been pre-configured with the required tolerations.

**1. Pods stuck in Pending - "untolerated taint"**

**Error in pod describe:**
```
0/2 nodes are available: 2 node(s) had untolerated taint(s)
Taints: CriticalAddonsOnly:NoSchedule
```

**Cause:** EKS Auto Mode nodes have taints to prevent regular pods from scheduling.

**Solution:** Add tolerations to your pod spec:
```yaml
spec:
  tolerations:
  - key: "CriticalAddonsOnly"
    operator: "Exists"
    effect: "NoSchedule"
  containers:
    - name: your-container
      image: your-image
```

All YAML files (elasticsearch.yaml, logstash.yaml, kibana.yaml, filebeat.yaml, k8s-deployment.yaml) already include this toleration.

**2. eksctl fails with "explicit deny in a service control policy"**

**Error:**
```
Error: describing cluster versions: operation error EKS: DescribeClusterVersions, 
AccessDeniedException: User is not authorized to perform: eks:DescribeClusterVersions 
with an explicit deny in a service control policy
```

**Cause:** AWS Organization Service Control Policies (SCPs) block EKS operations.

**Solution:** Use **Method B (AWS Console)** in Step 2 to create the cluster manually via AWS Console.

**3. kubectl cannot connect - "aws eks update-kubeconfig" fails with SCP error**

**Error:**
```
An error occurred (AccessDeniedException) when calling the DescribeCluster operation
```

**Solution:** Manually configure kubectl using information from AWS Console. Follow **Step 2.5 → Method 2** (Manual kubectl Configuration).

**4. kubectl timeout error - "dial tcp x.x.x.x:443: i/o timeout"**

**Error:**
```
E0228 07:12:35.494588 7150 memcache.go:265] couldn't get current server API group list: 
Get "https://xxxxx.eks.amazonaws.com/api?timeout=32s": dial tcp 172.31.x.x:443: i/o timeout
```

**Cause:** Your EC2 instance cannot reach the EKS cluster API endpoint. This usually happens when:
- Cluster endpoint access is set to **"Private only"** (most common)
- EC2 instance is in a different VPC than the cluster
- Security group blocking outbound HTTPS (443) from EC2
- EC2 instance doesn't have internet access (for Public endpoint)

**Solution Steps:**

**Option A: Change Cluster Endpoint Access to Public (Recommended for Testing)**

1. Go to **AWS Console** → **EKS** → **Clusters** → **ai-travel-agent**
2. Click the **Networking** tab
3. Under **Cluster endpoint access**, click **Manage**
4. Select one of these options:
   - **Public** (easiest - allows access from anywhere including your EC2)
   - **Public and private** (recommended - allows both internal and external access)
5. Click **Update**
6. Wait 2-3 minutes for the change to apply
7. Test again: `kubectl get nodes`

**Option B: Keep Private Endpoint (Requires EC2 in Same VPC)**

If you want to keep the endpoint private:

1. **Verify EC2 is in the same VPC as EKS cluster:**
   ```bash
   # Get EC2 VPC ID
   aws ec2 describe-instances \
     --instance-ids $(ec2-metadata --instance-id | cut -d ' ' -f 2) \
     --query 'Reservations[0].Instances[0].VpcId' \
     --output text
   
   # Compare with cluster VPC (from AWS Console EKS → Networking tab)
   ```

2. **Verify EC2 security group allows outbound HTTPS:**
   ```bash
   # Ensure outbound rule allows 0.0.0.0/0 on port 443
   ```

3. **Verify cluster security group allows inbound from EC2:**
   - Go to **EKS Console** → **ai-travel-agent** → **Networking** tab
   - Click the **Cluster security group**
   - Ensure it has an inbound rule allowing port 443 from your EC2 instance's security group or CIDR

**Option C: Use VPC Endpoint (Advanced)**

If using private endpoint, ensure:
- EC2 is in a subnet that has routes to the cluster API server ENIs
- DNS resolution is enabled in the VPC
- Private DNS is enabled

**Quick Test - Check Connectivity:**
```bash
# Get the cluster endpoint IP (extract from error or console)
# Try to telnet or curl
curl -k https://YOUR_CLUSTER_ENDPOINT

# Check if DNS resolves
nslookup YOUR_CLUSTER_ENDPOINT

# Check if port 443 is reachable
nc -vz YOUR_CLUSTER_ENDPOINT_IP 443
```

**4. kubectl authentication error - "the server has asked for the client to provide credentials"**

**Error:**
```
error: You must be logged in to the server (the server has asked for the client to provide credentials)
```

**Cause:** Your EC2 instance's IAM role is not authorized to access the EKS cluster. When you create a cluster via AWS Console, only the creator has access by default. The EC2 IAM role must be added to the cluster's aws-auth ConfigMap.

**Solution:**

You need to add your EC2 IAM role to the cluster's RBAC configuration. You have two options:

**Option A: Use AWS Console to Add Access (Recommended - No SCP Issues)**

1. Go to **AWS Console** → **EKS** → **Clusters** → **ai-travel-agent**
2. Click the **Access** tab
3. Click **Create access entry**
4. Configure:
   - **IAM principal ARN**: Enter your EC2 role ARN
     ```
     arn:aws:iam::201983195686:role/Travel-agent-role
     ```
   - **Type**: Select **Standard**
   - **Policy**: Choose **AmazonEKSClusterAdminPolicy** (for full access)
5. Click **Add**
6. Wait 1-2 minutes for changes to propagate
7. Test: `kubectl get nodes`

**Option B: Manually Edit aws-auth ConfigMap (If Console Method Not Available)**

This requires you to have initial access to the cluster. If you created the cluster via Console while logged in with a different user (not the EC2 role), you need to:

1. **From a machine with the creator credentials**, run:
   ```bash
   # Get the current aws-auth ConfigMap
   kubectl get configmap aws-auth -n kube-system -o yaml > aws-auth.yaml
   
   # Edit the file to add your EC2 IAM role
   vi aws-auth.yaml
   ```

2. **Add this section** under `mapRoles:` (replace with your actual IAM role ARN):
   ```yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: aws-auth
     namespace: kube-system
   data:
     mapRoles: |
       - rolearn: arn:aws:iam::201983195686:role/Travel-agent-role
         username: ec2-admin
         groups:
           - system:masters
       - rolearn: arn:aws:iam::201983195686:role/EKS-NodeGroup-Role
         username: system:node:{{EC2PrivateDNSName}}
         groups:
           - system:bootstrappers
           - system:nodes
   ```

3. **Apply the changes:**
   ```bash
   kubectl apply -f aws-auth.yaml
   ```

4. **Test from your EC2 instance:**
   ```bash
   kubectl get nodes
   ```

**Option C: Quick Fix - Use Same Credentials That Created the Cluster**

If you created the cluster using your AWS Console login (not the EC2 role), you can:

1. Configure AWS CLI with those credentials temporarily on EC2
2. Add the EC2 role to aws-auth using Option B above
3. Remove the temporary credentials
4. Continue using the EC2 IAM role

**To verify your current IAM identity:**
```bash
aws sts get-caller-identity
# Should show: arn:aws:sts::201983195686:assumed-role/Travel-agent-role/...
```

---

**Important Note on Access Entries:**

If you get a **Forbidden** error after following Option A above, it means:
- The access entry exists BUT doesn't have the right policy attached
- OR the access entry wasn't created properly

**To fix:**
1. Go to **EKS Console** → **Clusters** → **ai-travel-agent** → **Access** tab
2. Find your role entry: `Travel-agent-role`
3. Check if **Policy name** shows `AmazonEKSClusterAdminPolicy`
4. If not, delete the entry and recreate it with the correct policy
5. If the entry doesn't exist, create it as described in Option A above

---

**5. kubectl authorization error - "User cannot list resource 'nodes'"**

**Error:**
```
Error from server (Forbidden): nodes is forbidden: User "arn:aws:sts::201983195686:assumed-role/Travel-agent-role/..." 
cannot list resource "nodes" in API group "" at the cluster scope
```

**Cause:** Your IAM role has been authenticated (connected to cluster) but lacks authorization (RBAC permissions). This happens when:
- The access entry exists but has insufficient permissions
- The access entry was created without attaching a policy
- The wrong access policy was attached

**Solution:**

**Step 1: Check Current Access Entry**

1. Go to **AWS Console** → **EKS** → **Clusters** → **ai-travel-agent**
2. Click the **Access** tab
3. Look for an entry with your role ARN: `arn:aws:iam::201983195686:role/Travel-agent-role`

**Step 2: Fix the Access Entry**

**If the entry exists with wrong/no policy:**
1. Select the entry (checkbox)
2. Click **Delete**
3. Confirm deletion
4. Click **Create access entry**
5. Configure:
   - **IAM principal ARN**: `arn:aws:iam::201983195686:role/Travel-agent-role`
   - **Type**: **Standard**
   - Click **Next**
6. **Add Policy:**
   - Select **AmazonEKSClusterAdminPolicy**
   - Click **Next**
7. Review and click **Create**

**If the entry doesn't exist:**
1. Follow steps 4-7 above to create it

**Step 3: Verify the Policy is Attached**

After creating/updating:
1. In the **Access** tab, find your role entry
2. Verify under **Policy name** it shows: `AmazonEKSClusterAdminPolicy`
3. The **Access scope** should show: `cluster`

**Step 4: Test**

Wait 30-60 seconds, then test:
```bash
kubectl get nodes
# Should now show 2 nodes in Ready state

kubectl get pods --all-namespaces
# Should list all pods
```

**Alternative: Add Specific Permissions via Access Policy**

If you want to grant specific permissions instead of full admin:

1. In **Access** tab, click the access entry
2. Click **Edit**
3. Choose one of these policies:
   - **AmazonEKSClusterAdminPolicy** - Full cluster access (recommended for testing)
   - **AmazonEKSAdminPolicy** - Admin access to all namespaces
   - **AmazonEKSEditPolicy** - Edit resources in specific namespaces
   - **AmazonEKSViewPolicy** - Read-only access

**Quick Verification Commands:**

```bash
# Check your current permissions
kubectl auth can-i get nodes
# Should return: yes

kubectl auth can-i create pods
# Should return: yes

# List all your permissions
kubectl auth can-i --list
```

**6. Node Group creation failed - "Instances failed to join the kubernetes cluster"**

**Error in AWS Console:**
```
NodeCreationFailure: Instances failed to join the kubernetes cluster
Health issues: i-xxxxx, i-xxxxx (EC2 instances exist but not joining cluster)
```

**Cause:** This happens when:
- **aws-auth ConfigMap** is missing or doesn't have the node IAM role configured (most common)
- Node IAM role missing required policies
- Security group blocking communication between nodes and control plane
- Incorrect AMI or Kubernetes version mismatch

**Solution Steps:**

**Step 1: Check if aws-auth ConfigMap exists**

```bash
# Check if aws-auth ConfigMap exists
kubectl get configmap aws-auth -n kube-system

# If it doesn't exist (error: "configmap 'aws-auth' not found"), you need to create it
```

**Step 2: Create or Fix aws-auth ConfigMap**

**If ConfigMap doesn't exist, create it:**

```bash
# Get your node group IAM role ARN
# Replace with your actual role ARN (e.g., arn:aws:iam::201983195686:role/EKS-NodeGroup-Role)

cat > aws-auth.yaml << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    - rolearn: arn:aws:iam::201983195686:role/EKS-NodeGroup-Role
      username: system:node:{{EC2PrivateDNSName}}
      groups:
        - system:bootstrappers
        - system:nodes
EOF

# Apply the ConfigMap
kubectl apply -f aws-auth.yaml

# Verify it was created
kubectl get configmap aws-auth -n kube-system
```

**If ConfigMap exists but nodes still not joining:**

```bash
# Get the current ConfigMap
kubectl get configmap aws-auth -n kube-system -o yaml

# Check if your node IAM role ARN is listed
# If not, edit it:
kubectl edit configmap aws-auth -n kube-system

# Add this section under mapRoles: (replace with your node role ARN)
# - rolearn: arn:aws:iam::201983195686:role/EKS-NodeGroup-Role
#   username: system:node:{{EC2PrivateDNSName}}
#   groups:
#     - system:bootstrappers
#     - system:nodes
```

**Step 3: Delete the Failed Node Group**

1. Go to **AWS Console** → **EKS** → **Clusters** → **ai-travel-agent** → **Compute** tab
2. Select the failed node group (ng-1)
3. Click **Delete**
4. Confirm deletion
5. Wait for deletion to complete (2-3 minutes)

**Step 4: Verify Node IAM Role Has Required Policies**

1. Go to **IAM Console** → **Roles** → **EKS-NodeGroup-Role**
2. Verify these policies are attached:
   - **AmazonEKSWorkerNodePolicy**
   - **AmazonEKS_CNI_Policy**
   - **AmazonEC2ContainerRegistryReadOnly**
3. If missing, attach them:
   - Click **Add permissions** → **Attach policies**
   - Search and select the missing policies
   - Click **Add permissions**

**Step 5: Create New Node Group**

1. Go to **EKS Console** → **Clusters** → **ai-travel-agent** → **Compute** tab
2. Click **Add node group**
3. Configure:
   - **Name**: `ng-1`
   - **Node IAM role**: Select `EKS-NodeGroup-Role`
   - **Instance type**: t3.medium
   - **Desired/Min/Max size**: 2/2/4
4. Click through and **Create**
5. Wait 5-7 minutes for nodes to join

**Step 6: Verify Nodes Joined Successfully**

```bash
# Check if nodes are joining
kubectl get nodes -w

# Should show nodes in Ready state after 5-7 minutes

# Check system pods are running
kubectl get pods -n kube-system

# Check aws-auth ConfigMap is correct
kubectl describe configmap aws-auth -n kube-system
```

**Quick Diagnostic Commands:**

```bash
# Check if any nodes exist
kubectl get nodes

# If no nodes, check aws-auth
kubectl get configmap aws-auth -n kube-system -o yaml

# Check node group status in AWS
aws eks describe-nodegroup \
  --cluster-name ai-travel-agent \
  --nodegroup-name ng-1 \
  --region us-east-1 \
  --query 'nodegroup.status'
```

**Alternative: Use EKS Console to Check Node Group Health**

1. **EKS Console** → **Clusters** → **ai-travel-agent** → **Compute** tab
2. Click on the node group name
3. Check **Health issues** section for detailed error messages
4. Check **Configuration** → **Details** to verify:
   - IAM role is correct
   - Subnets are correct
   - AMI type matches cluster version

**Important Note: If Nodes are Ready but Node Group Creation Fails**

If `kubectl get nodes` shows nodes in `Ready` state:
```bash
NAME                  STATUS   ROLES    AGE   VERSION
i-02783f5c0498c079a   Ready    <none>   7h    v1.35.0-eks-xxx
i-0eb831301f7c53a37   Ready    <none>   7h    v1.35.0-eks-xxx
```

**You can proceed with the deployment!** The node group is just a management interface in AWS Console. What matters is that:
- Nodes are joined to the cluster (`STATUS = Ready`)
- System pods are running (`kubectl get pods -n kube-system`)
- You can deploy workloads

Even though the node group shows as failed or doesn't appear in the Console, if `kubectl get nodes` shows Ready nodes, your cluster is functional. Continue to the next steps (install EBS CSI driver, deploy Elasticsearch, etc.).

---

**7. Pods stuck in Pending state**

**Error:**
```
NAME                     READY   STATUS    RESTARTS   AGE
elasticsearch-xxx        0/1     Pending   0          28m
```

**Cause:** Most commonly, this happens when:
- **PersistentVolumeClaim (PVC) cannot be bound** - EBS CSI driver not installed (most common for Elasticsearch)
- Insufficient resources on nodes
- Node taints preventing scheduling

**Solution Steps:**

**Step 1: Check why pod is pending**
```bash
# Describe the pending pod to see the exact reason
kubectl describe pod -n logging <pod-name>

# Check PVC status
kubectl get pvc -n logging
```

**If PVC shows "Pending" status:**

This means the EBS CSI driver is not installed. The Elasticsearch pod needs a PersistentVolume but Kubernetes cannot provision it.

**Fix: Install EBS CSI Driver**

Follow the steps in **Step 2 → Install Amazon EBS CSI Driver** section above, then:

```bash
# After installing EBS CSI driver, check PVC again
kubectl get pvc -n logging

# Should change from Pending to Bound within 1-2 minutes

# Check StorageClass
kubectl get storageclass

# Wait for pod to start
kubectl get pods -n logging -w
```

**If you see "Insufficient cpu" or "Insufficient memory" in describe output:**

```bash
# Check node resources
kubectl describe nodes

# Either:
# 1. Delete unnecessary pods to free resources
# 2. Add more nodes to the cluster (increase desired capacity in node group)
# 3. Use smaller resource requests in elasticsearch.yaml
```

**If you see "0/2 nodes are available: 2 node(s) had taint":**

```bash
# Remove taints from nodes
kubectl taint nodes --all node-role.kubernetes.io/master-

# Or update your pod spec to add tolerations
```

**Quick Fix for Elasticsearch Stuck in Pending:**

```bash
# 1. Check if EBS CSI driver is installed
kubectl get pods -n kube-system | grep ebs-csi

# If no results, install it via AWS Console:
# EKS → Clusters → ai-travel-agent → Add-ons → Get more add-ons → Amazon EBS CSI Driver

# 2. Wait 2-3 minutes for driver to be ready
kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-ebs-csi-driver

# 3. Check PVC status - should change from Pending to Bound
kubectl get pvc -n logging

# 4. Pod should start automatically once PVC is Bound
kubectl get pods -n logging -w
```

**8. EBS CSI Driver add-on stuck in "Creating" state**

**Symptoms:**
```
Add-on status: Creating (for 10+ minutes)
IAM role for service account (IRSA): Not set
```

**Cause:** Add-on is waiting for IAM role configuration. Without OIDC provider (which you can't create), it stays stuck.

**Solution:**

1. **Delete the stuck add-on:**
   - **EKS Console** → **Clusters** → **ai-travel-agent** → **Add-ons**
   - Select **Amazon EBS CSI Driver** → **Remove**

2. **Attach EBS policy to node role:**
   - **IAM Console** → **Roles** → **EKS-NodeGroup-Role**
   - **Add permissions** → Attach **AmazonEBSCSIDriverPolicy**

3. **Deploy CSI driver manually:**
   ```bash
   kubectl apply -k "github.com/kubernetes-sigs/aws-ebs-csi-driver/deploy/kubernetes/overlays/stable/?ref=release-1.35"
   
   # Verify
   kubectl get pods -n kube-system | grep ebs-csi
   # Should show Running within 2-3 minutes
   ```

4. **Test it works:**
   ```bash
   kubectl get storageclass
   kubectl apply -f elasticsearch.yaml
   kubectl get pvc -n logging -w
   # Should show: Bound
   ```

See the detailed section "Troubleshooting: EBS CSI Add-on Stuck in Creating State" in Step 2 for more details.

**9. LoadBalancer stuck in Pending**
```bash
# Check service events
kubectl describe svc streamlit-service

# EKS should automatically provision an ELB, but may take 3-5 minutes
```

**10. No logs appearing in Kibana**
```bash
# Check Filebeat is running
kubectl get pods -n logging | grep filebeat

# Check Filebeat logs
kubectl logs -n logging daemonset/filebeat --tail=100

# Verify Logstash is receiving data
kubectl logs -n logging deployment/logstash --tail=100
```

**11. Can't access Kibana via NodePort**
```bash
# Check node security group allows port 30601
# Get the security group ID
aws ec2 describe-instances \
  --filters "Name=tag:eks:cluster-name,Values=ai-travel-agent" \
  --query 'Reservations[*].Instances[*].SecurityGroups[*].[GroupId]' \
  --output text

# Add inbound rule for port 30601
aws ec2 authorize-security-group-ingress \
  --group-id <security-group-id> \
  --protocol tcp \
  --port 30601 \
  --cidr 0.0.0.0/0  # Or restrict to your IP
```

**12. Cannot create OIDC provider for EBS CSI Driver IAM role**

**Error:**
```
User is not authorized to perform: iam:CreateOpenIDConnectProvider because no permissions boundary 
allows the iam:CreateOpenIDConnectProvider action
```

**Cause:** Your IAM user/role lacks permission to create OIDC providers. Common in sandbox/restricted AWS accounts.

**Solution: Use Node IAM Role Workaround**

Since you can't create OIDC provider, grant EBS permissions directly to the node group IAM role:

1. Go to **IAM Console** → **Roles** → Find `EKS-NodeGroup-Role`
2. Click **Add permissions** → **Attach policies**
3. Search and attach: **AmazonEBSCSIDriverPolicy**
4. Restart CSI driver:
   ```bash
   kubectl rollout restart deployment ebs-csi-controller -n kube-system
   ```
5. Test PVC creation:
   ```bash
   kubectl get pvc -n logging
   # Should show Bound status
   ```

**Alternative:** Ask your AWS administrator to create the OIDC provider for:
- Provider URL: `https://oidc.eks.ap-south-1.amazonaws.com/id/5EB4245A0FA5AF1A52DED225E0F26411`
- Audience: `sts.amazonaws.com`

See the "Troubleshooting: Cannot Create OIDC Provider" section in Step 2 for detailed instructions.

---
## Startup Resources

3. Get EC2 Public IP
# Get your EC2 public IP
curl http://checkip.amazonaws.com
# Or
ec2-metadata --public-ipv4 | cut -d ' ' -f 2
4. Access Streamlit App
Open browser: http://<EC2_PUBLIC_IP>:8501

# 1. Add security group rules for ports 5601 and 9200
export INSTANCE_ID=$(ec2-metadata --instance-id | cut -d ' ' -f 2)
export SG_ID=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' --output text)

# Allow Kibana (5601) and Elasticsearch (9200)
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 5601 --cidr 0.0.0.0/0 --region ap-south-1
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 9200 --cidr 0.0.0.0/0 --region ap-south-1

# 2. Start port-forwards
kubectl port-forward -n logging svc/kibana 5601:5601 --address 0.0.0.0 &
kubectl port-forward -n logging svc/elasticsearch 9200:9200 --address 0.0.0.0 &

# 3. Get EC2 public IP
curl http://checkip.amazonaws.com

# 4. Access in browser:
# Kibana: http://<EC2_PUBLIC_IP>:5601
# Elasticsearch: http://<EC2_PUBLIC_IP>:9200
# Streamlit: http://<EC2_PUBLIC_IP>:8501 (already running)

## Cleanup Resources

```bash
# Delete Kubernetes resources
kubectl delete -f k8s-deployment.yaml
kubectl delete -f filebeat.yaml
kubectl delete -f kibana.yaml
kubectl delete -f logstash.yaml
kubectl delete -f elasticsearch.yaml
kubectl delete namespace logging

# Delete EKS cluster
eksctl delete cluster --name ai-travel-agent --region us-east-1

# Delete ECR repository
aws ecr delete-repository \
  --repository-name streamlit-app \
  --region us-east-1 \
  --force

# Terminate EC2 instance via AWS Console
```

---

## Cost Estimates (US-East-1)

- **EKS Cluster**: ~$73/month (control plane)
- **2x t3.medium nodes**: ~$60/month
- **ELB**: ~$16/month + data transfer
- **EBS Volume (2GB)**: ~$0.20/month
- **ECR Storage**: ~$0.10/GB/month
- **Total**: ~$150-170/month

**Note**: Use `eksctl delete cluster` when not in use to avoid charges.

---

## Next Steps

1. **Set up IRSA**: Configure IAM Roles for Service Accounts for pod-level permissions
2. **Enable HTTPS**: Use ACM certificates with Application Load Balancer
3. **CloudWatch Integration**: Set up CloudWatch Container Insights for additional monitoring
4. **Elasticsearch Retention**: Configure index lifecycle management (ILM) policies
5. **Backup Strategy**: Set up automated snapshots for Elasticsearch data to S3
6. **Auto Scaling**: Implement Horizontal Pod Autoscaling (HPA) for the Streamlit app
7. **Cost Optimization**: Set up AWS Cost Explorer alerts and consider Spot instances for worker nodes

---

## Security Recommendations

1. **IAM Roles**: This deployment uses IAM roles for EC2, which is more secure than access keys
2. **Update Security Groups**: Restrict NodePort 30601 and SSH (22) to your IP only
3. **Use Service Account IAM Roles**: Attach IAM roles to Kubernetes service accounts for pod-level permissions (IRSA)
4. **Enable Network Policies**: Use Calico or AWS VPC CNI network policies
5. **Rotate Secrets**: Regularly rotate GROQ_API_KEY
6. **Enable EKS Logging**: Enable control plane logs in EKS settings
7. **Update Images**: Regularly update Elasticsearch, Kibana, Logstash, Filebeat images
8. **Least Privilege**: Review and restrict IAM role permissions after initial setup

---

## References

- [EKS Documentation](https://docs.aws.amazon.com/eks/)
- [Elastic Stack on Kubernetes](https://www.elastic.co/guide/en/cloud-on-k8s/current/index.html)
- [eksctl Documentation](https://eksctl.io/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)

#
# 
#
# ## Using a Single IAM Role for Both EKS Cluster and Node Group
#
# 1. **Create a single IAM role with the following trust relationship:**
#
#    Trust Relationship (for both EKS and EC2):
#    {
#      "Version": "2012-10-17",
#      "Statement": [
#        {
#          "Effect": "Allow",
#          "Principal": {
#            "Service": [
#              "eks.amazonaws.com",
#              "ec2.amazonaws.com"
#            ]
#          },
#          "Action": "sts:AssumeRole"
#        }
#      ]
#    }
#
# 2. **Attach this inline policy to the role:**
#    {
#      "Version": "2012-10-17",
#      "Statement": [
#        {
#          "Effect": "Allow",
#          "Action": [
#            "eks:ListClusters",
#            "eks:DescribeCluster",
#            "eks:CreateCluster",
#            "eks:DeleteCluster",
#            "eks:UpdateClusterConfig",
#            "eks:UpdateClusterVersion",
#            "eks:ListNodegroups",
#            "eks:DescribeNodegroup",
#            "eks:CreateNodegroup",
#            "eks:UpdateNodegroupConfig",
#            "eks:UpdateNodegroupVersion",
#            "eks:DeleteNodegroup",
#            "eks:AccessKubernetesApi",
#            "eks:TagResource",
#            "eks:UntagResource",
#            "eks:ListUpdates",
#            "eks:DescribeUpdate",
#            "eks:DescribeClusterVersions",
#            "ec2:Describe*",
#            "ec2:CreateTags",
#            "ec2:DeleteTags",
#            "ec2:CreateSecurityGroup",
#            "ec2:DeleteSecurityGroup",
#            "ec2:AuthorizeSecurityGroupIngress",
#            "ec2:AuthorizeSecurityGroupEgress",
#            "ec2:RevokeSecurityGroupIngress",
#            "ec2:RevokeSecurityGroupEgress",
#            "ec2:CreateSubnet",
#            "ec2:DeleteSubnet",
#            "ec2:CreateVpc",
#            "ec2:DeleteVpc",
#            "ec2:CreateInternetGateway",
#            "ec2:DeleteInternetGateway",
#            "ec2:AttachInternetGateway",
#            "ec2:DetachInternetGateway",
#            "ec2:CreateRouteTable",
#            "ec2:DeleteRouteTable",
#            "ec2:CreateRoute",
#            "ec2:DeleteRoute",
#            "ec2:AssociateRouteTable",
#            "ec2:DisassociateRouteTable",
#            "ec2:CreateNatGateway",
#            "ec2:DeleteNatGateway",
#            "ec2:AllocateAddress",
#            "ec2:ReleaseAddress",
#            "ec2:DescribeAddresses",
#            "ec2:DescribeInternetGateways",
#            "ec2:DescribeNatGateways",
#            "ec2:DescribeRouteTables",
#            "ec2:DescribeSecurityGroups",
#            "ec2:DescribeSubnets",
#            "ec2:DescribeVpcs",
#            "ec2:DescribeInstances",
#            "ec2:DescribeImages",
#            "ec2:DescribeKeyPairs",
#            "ec2:DescribeNetworkInterfaces",
#            "ec2:DescribeTags",
#            "iam:PassRole",
#            "ecr:GetAuthorizationToken",
#            "ecr:BatchCheckLayerAvailability",
#            "ecr:GetDownloadUrlForLayer",
#            "ecr:BatchGetImage",
#            "ecr:GetRepositoryPolicy",
#            "ecr:DescribeRepositories",
#            "ecr:ListImages",
#            "ecr:DescribeImages",
#            "ecr:ListTagsForResource",
#            "ecr:DescribeImageScanFindings",
#            "ssm:GetParameter"
#          ],
#          "Resource": "*"
#        }
#      ]
#    }
#
# 3. **Steps to use this role with eksctl:**
#    - Save the following config as `eksctl-config.yaml` on your EC2 instance:
#
#      apiVersion: eksctl.io/v1alpha5
#      kind: ClusterConfig
#
#      metadata:
#        name: ai-travel-agent
#        region: ap-south-1
#
#      iam:
#        serviceRoleARN: arn:aws:iam::<account-id>:role/<your-eks-role>
#
#      nodeGroups:
#        - name: ng-1
#          instanceType: t3.medium
#          desiredCapacity: 2
#          iam:
#            instanceRoleARN: arn:aws:iam::<account-id>:role/<your-eks-role>
#
#    - Run:
#      eksctl create cluster -f eksctl-config.yaml
#
#    eksctl will use your provided role for both the cluster and node group.
