Yes. Now we start **Phase 3 — Terraform AWS Infrastructure**.

We'll build the infrastructure incrementally rather than putting everything into one large Terraform file.

## Phase 3 architecture

```text
                         AWS
                          |
                     ap-south-1
                          |
                    ┌─────┴─────┐
                    │    VPC    │
                    └─────┬─────┘
                          |
          ┌───────────────┴───────────────┐
          │                               │
     Public Subnets                  Private Subnets
          │                               │
     Load Balancer                    EKS Nodes
                                          |
                                    Backend Pods
                                          |
                                          v
                                      RDS MySQL

ECR
 ├── aws-community-frontend
 └── aws-community-backend
```

### Terraform phases

We'll do:

```text
3.1  Terraform installation/check
3.2  Project structure
3.3  AWS provider
3.4  VPC + subnets
3.5  Security groups
3.6  ECR
3.7  RDS MySQL
3.8  IAM
3.9  EKS
3.10 Outputs
3.11 terraform plan/apply
```

**Important:** We will create RDS and EKS later in this phase. This prevents expensive resources from being created before the networking is correct.

---

# Step 3.1 — Check Terraform

On your EC2:

```bash
terraform version
```

Also:

```bash
aws sts get-caller-identity
```

And:

```bash
aws configure get region
```

We will use:

```text
ap-south-1
```

for this project.

If your Terraform is already installed, don't reinstall it.

---

# Step 3.2 — Create Terraform directory

From your project:

```bash
cd ~/AWS-Community-Registration-application

mkdir -p terraform

cd terraform
```

Create the structure:

```bash
mkdir -p modules

touch provider.tf
touch variables.tf
touch main.tf
touch outputs.tf

touch vpc.tf
touch security-groups.tf
touch ecr.tf
touch rds.tf
touch iam.tf
touch eks.tf

touch terraform.tfvars
touch .gitignore
```

Check:

```bash
find . -maxdepth 2 -type f | sort
```

You'll have:

```text
terraform/
├── ecr.tf
├── eks.tf
├── iam.tf
├── main.tf
├── outputs.tf
├── provider.tf
├── rds.tf
├── security-groups.tf
├── terraform.tfvars
├── variables.tf
├── vpc.tf
└── .gitignore
```

---

# Step 3.3 — Terraform provider

Open:

```bash
nano provider.tf
```

Use:

```hcl
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "AWS-Community-Registration"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
```

We're deliberately using the current AWS provider major version rather than hardcoding an old version.

---

# Step 3.4 — Variables

Open:

```bash
nano variables.tf
```

Use:

```hcl
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "aws-community"
}

variable "vpc_cidr" {
  description = "VPC CIDR"
  type        = string
  default     = "10.0.0.0/16"
}

variable "db_name" {
  description = "RDS database name"
  type        = string
  default     = "aws_community"
}

variable "db_username" {
  description = "RDS username"
  type        = string
  default     = "community_app"
}

variable "db_password" {
  description = "RDS password"
  type        = string
  sensitive   = true
}

variable "eks_cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "aws-community-eks"
}
```

---

# Step 3.5 — Terraform variables file

Open:

```bash
nano terraform.tfvars
```

Use:

```hcl
aws_region        = "ap-south-1"
environment       = "dev"
project_name      = "aws-community"
vpc_cidr          = "10.0.0.0/16"
db_name           = "aws_community"
db_username       = "community_app"
db_password       = "REPLACE_WITH_STRONG_PASSWORD"
eks_cluster_name  = "aws-community-eks"
```

**Do not commit this file to GitHub.**

---

# Step 3.6 — Terraform `.gitignore`

Open:

```bash
nano .gitignore
```

Use:

```text
.terraform/
terraform.tfstate
terraform.tfstate.*
terraform.tfvars
*.tfplan
crash.log
crash.*.log
```

Also make sure the project-level `.gitignore` contains:

```text
terraform/terraform.tfvars
terraform/.terraform/
terraform/terraform.tfstate
terraform/terraform.tfstate.*
```

This is important because `terraform.tfstate` can contain sensitive infrastructure information.

---

# Step 3.7 — Initialize Terraform

Run:

```bash
terraform init
```

Then:

```bash
terraform version
```

You should see the AWS provider downloaded.

---

# Step 3.8 — Create VPC

Now we'll create the networking foundation.

Open:

```bash
nano vpc.tf
```

Use:

```hcl
data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.project_name}-${var.environment}-vpc"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-${var.environment}-igw"
  }
}

resource "aws_subnet" "public" {
  count = 2

  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-${var.environment}-public-${count.index + 1}"

    "kubernetes.io/role/elb" = "1"
  }
}

resource "aws_subnet" "private" {
  count = 2

  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.project_name}-${var.environment}-private-${count.index + 1}"

    "kubernetes.io/role/internal-elb" = "1"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-public-rt"
  }
}

resource "aws_route_table_association" "public" {
  count = 2

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_eip" "nat" {
  domain = "vpc"

  tags = {
    Name = "${var.project_name}-${var.environment}-nat-eip"
  }
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id

  depends_on = [
    aws_internet_gateway.main
  ]

  tags = {
    Name = "${var.project_name}-${var.environment}-nat"
  }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-private-rt"
  }
}

resource "aws_route_table_association" "private" {
  count = 2

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}
```

This creates:

```text
VPC 10.0.0.0/16

Public:
10.0.0.0/24
10.0.1.0/24

Private:
10.0.10.0/24
10.0.11.0/24
```

---

# Step 3.9 — VPC outputs

Open:

```bash
nano outputs.tf
```

Start with:

```hcl
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}
```

We'll add ECR/RDS/EKS outputs later.

---

# Step 3.10 — Validate

Run:

```bash
terraform fmt
```

Then:

```bash
terraform validate
```

Expected:

```text
Success! The configuration is valid.
```

Then:

```bash
terraform plan
```

Review carefully.

At this point Terraform should primarily be planning:

```text
VPC
Internet Gateway
Public Subnets
Private Subnets
Route Tables
NAT Gateway
Elastic IP
```

---

# Step 3.11 — Apply only the VPC

For now, I recommend:

```bash
terraform apply
```

Review the resources before entering:

```text
yes
```

Terraform will create the networking.

Then:

```bash
terraform output
```

You should get your VPC and subnet IDs.

---

# Important cost warning

The **NAT Gateway is not free** and can generate charges.

For our production-style architecture, I included it because EKS nodes in private subnets need outbound access for things such as pulling images and reaching AWS services.

For a low-cost learning environment, we can later modify the architecture to reduce NAT Gateway costs, depending on how you want to operate the lab.

Also remember to destroy resources when you're finished practicing:

```bash
terraform destroy
```

Don't run that while the application is in use.

---

# What we have after this step

```text
                    AWS
                     |
                    VPC
               10.0.0.0/16
                     |
          ┌──────────┴──────────┐
          │                     │
          v                     v
    Public Subnets        Private Subnets
          │                     │
          v                     v
    Load Balancer          EKS Nodes
          │                     │
          │                     v
          │                Backend Pods
          │                     │
          │                     v
          │                  RDS
          │
       Internet
```

Then we'll add ECR:

```text
ECR
├── aws-community-frontend
└── aws-community-backend
```

Then RDS:

```text
Private Subnets
      |
      v
RDS MySQL
```

Then EKS:

```text
Private Subnets
      |
      v
EKS Node Group
```

---

## Your immediate task

Don't create RDS or EKS yet.

Run these commands from:

```bash
cd ~/AWS-Community-Registration-application/terraform
```

```bash
terraform init
terraform fmt
terraform validate
terraform plan
```

If the plan looks correct, run:

```bash
terraform apply
```

Then send me the output of:

```bash
terraform output
```

**After the VPC is successfully created, we'll do Phase 3.2 — ECR + RDS MySQL with Terraform.**
