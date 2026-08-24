Yes. Docker is our Phase 2 foundation. Now we'll move to **Phase 2B — AWS ECR**, before Terraform and EKS.

Our immediate goal is:

```text
EC2
 │
 ├── Frontend Docker Image
 └── Backend Docker Image
          │
          ▼
       AWS ECR
          │
          ├── aws-community-frontend
          └── aws-community-backend
```

We will **not push MySQL to ECR**. In the eventual AWS architecture, MySQL will become **Amazon RDS MySQL**.

## Phase 2B — Create ECR repositories

### 1. Verify AWS CLI

On your EC2:

```bash
aws --version
```

Then:

```bash
aws sts get-caller-identity
```

You should get your AWS account information.

Also check your region:

```bash
aws configure get region
```

If you're using Mumbai:

```bash
aws configure set region ap-south-1
```

Verify:

```bash
aws configure get region
```

Expected:

```text
ap-south-1
```

---

## 2. Check Docker images

```bash
cd ~/AWS-Community-Registration-application

docker images
```

You should have images for your frontend and backend.

If the images were created by Compose, also run:

```bash
docker compose images
```

---

## 3. Create ECR repositories

Create the backend repository:

```bash
aws ecr create-repository \
  --repository-name aws-community-backend \
  --region ap-south-1
```

Create the frontend repository:

```bash
aws ecr create-repository \
  --repository-name aws-community-frontend \
  --region ap-south-1
```

Check:

```bash
aws ecr describe-repositories \
  --region ap-south-1
```

You should see:

```text
aws-community-backend
aws-community-frontend
```

---

## 4. Get your AWS account ID

```bash
aws sts get-caller-identity \
  --query Account \
  --output text
```

For example:

```text
123456789012
```

We'll refer to that as:

```text
ACCOUNT_ID
```

Your ECR registry will be:

```text
ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com
```

---

## 5. Authenticate Docker with ECR

Run:

```bash
aws ecr get-login-password \
  --region ap-south-1 | \
docker login \
  --username AWS \
  --password-stdin \
  ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com
```

Replace:

```text
ACCOUNT_ID
```

with your actual AWS account ID.

Expected:

```text
Login Succeeded
```

---

# 6. Identify your Docker image names

Run:

```bash
docker compose images
```

You may see something similar to:

```text
CONTAINER             REPOSITORY
community-frontend    aws-community-registration-application-frontend
community-backend     aws-community-registration-application-backend
community-mysql       mysql
```

We'll tag the frontend and backend images.

---

# 7. Tag the backend image

First identify the exact image:

```bash
docker images
```

Suppose the backend image is:

```text
aws-community-registration-application-backend:latest
```

Tag it:

```bash
docker tag \
  aws-community-registration-application-backend:latest \
  ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/aws-community-backend:1.0
```

Also create a `latest` tag:

```bash
docker tag \
  aws-community-registration-application-backend:latest \
  ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/aws-community-backend:latest
```

---

# 8. Tag the frontend image

```bash
docker tag \
  aws-community-registration-application-frontend:latest \
  ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/aws-community-frontend:1.0
```

And:

```bash
docker tag \
  aws-community-registration-application-frontend:latest \
  ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/aws-community-frontend:latest
```

Check:

```bash
docker images
```

You should now see something like:

```text
REPOSITORY
ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/aws-community-backend
ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/aws-community-frontend
```

---

# 9. Push backend

```bash
docker push \
  ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/aws-community-backend:1.0
```

Then:

```bash
docker push \
  ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/aws-community-backend:latest
```

---

# 10. Push frontend

```bash
docker push \
  ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/aws-community-frontend:1.0
```

Then:

```bash
docker push \
  ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/aws-community-frontend:latest
```

---

# 11. Verify ECR

Backend:

```bash
aws ecr list-images \
  --repository-name aws-community-backend \
  --region ap-south-1
```

Frontend:

```bash
aws ecr list-images \
  --repository-name aws-community-frontend \
  --region ap-south-1
```

You should see:

```text
1.0
latest
```

---

# 12. Our architecture now

We've moved from:

```text
EC2
 |
 Docker
 |
 Containers
```

to:

```text
EC2
 |
 Docker
 |
 +------------------+
 |                  |
 v                  v
Frontend           Backend
 |                  |
 +--------+---------+
          |
          v
       MySQL
```

and additionally:

```text
                 AWS
                  |
                  v
                 ECR
            /            \
           /              \
          v                v
   Frontend Image     Backend Image
```

---

# Next Phase — Terraform

Once ECR is confirmed, we'll start **Phase 3 — Terraform AWS Infrastructure**.

We'll build it in this order:

```text
Terraform
   |
   +── Provider
   |
   +── VPC
   |    ├── Public Subnets
   |    └── Private Subnets
   |
   +── Security Groups
   |
   +── ECR
   |
   +── RDS MySQL
   |
   +── IAM
   |
   +── EKS
   |    ├── Cluster
   |    └── Node Group
   |
   └── Outputs
```

And the final AWS architecture will be:

```text
                         Internet
                            |
                            v
                     Load Balancer
                            |
                            v
                         EKS
                   ┌────────┴────────┐
                   │                 │
                   v                 v
              Frontend Pods     Backend Pods
                                      |
                                      |
                               Private Network
                                      |
                                      v
                                  RDS MySQL
```

**For this step, run the ECR commands through `docker push` and verify with `aws ecr list-images`. Once that succeeds, we'll start Terraform with the VPC rather than creating everything in one huge `main.tf`.**
