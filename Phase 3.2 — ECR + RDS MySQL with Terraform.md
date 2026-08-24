Absolutely. Now we'll implement **Phase 3.2 — ECR + RDS MySQL with Terraform**.

At the end of this phase:

```text
                         AWS
                          |
                    ┌─────┴─────┐
                    |    VPC    |
                    └─────┬─────┘
                          |
             ┌────────────┴────────────┐
             |                         |
        Public Subnets            Private Subnets
             |                         |
             |                    ┌────┴────┐
             |                    |         |
             |                    v         v
             |                  RDS       EKS
             |
             v
        Load Balancer

ECR
├── aws-community-frontend
└── aws-community-backend
```

We'll do **ECR first**, then **RDS**, then test the Terraform configuration.

---

# Phase 3.2.1 — ECR with Terraform

You already created ECR repositories manually in the previous phase. **Don't create duplicate repositories.**

We now want Terraform to manage them.

## 1. Open `ecr.tf`

```bash
cd ~/AWS-Community-Registration-application/terraform

nano ecr.tf
```

Add:

```hcl
resource "aws_ecr_repository" "frontend" {
  name                 = "${var.project_name}-frontend"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name = "${var.project_name}-frontend"
  }
}

resource "aws_ecr_repository" "backend" {
  name                 = "${var.project_name}-backend"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name = "${var.project_name}-backend"
  }
}
```

This creates:

```text
aws-community-frontend
aws-community-backend
```

with:

```text
Scan on push = enabled
Encryption   = AES256
```

---

# 2. Add ECR outputs

Open:

```bash
nano outputs.tf
```

Append:

```hcl
output "frontend_ecr_repository_url" {
  description = "Frontend ECR repository URL"
  value       = aws_ecr_repository.frontend.repository_url
}

output "backend_ecr_repository_url" {
  description = "Backend ECR repository URL"
  value       = aws_ecr_repository.backend.repository_url
}
```

---

# 3. Check existing ECR repositories

Because you created them manually earlier, run:

```bash
aws ecr describe-repositories \
  --repository-names aws-community-frontend aws-community-backend \
  --region ap-south-1
```

If they exist, Terraform will initially report that they need to be created.

**Don't run `terraform apply` yet.**

We need to import the existing repositories into Terraform.

---

# 4. Import existing ECR repositories

Run:

```bash
terraform import \
  aws_ecr_repository.frontend \
  aws-community-frontend
```

Then:

```bash
terraform import \
  aws_ecr_repository.backend \
  aws-community-backend
```

Expected output will look similar to:

```text
Import successful!
```

Now run:

```bash
terraform plan
```

Terraform should understand that these repositories already exist.

You should **not** see:

```text
+ create aws_ecr_repository.frontend
+ create aws_ecr_repository.backend
```

If you see changes such as image scanning or encryption configuration, that's okay; review them before applying.

---

# Phase 3.2.2 — RDS MySQL

Now we're going to move the database from:

```text
MySQL Docker container
```

to:

```text
Amazon RDS MySQL
```

This is the architecture we'll eventually use with EKS:

```text
EKS Backend Pods
       |
       | TCP 3306
       v
   RDS MySQL
       |
       v
Private Subnets
```

---

# 5. Create the RDS security group

Open:

```bash
nano security-groups.tf
```

Add:

```hcl
resource "aws_security_group" "rds" {
  name        = "${var.project_name}-${var.environment}-rds-sg"
  description = "Security group for AWS Community RDS"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "MySQL from VPC"
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "Allow outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-rds-sg"
  }
}
```

### Important

We're allowing MySQL from:

```text
10.0.0.0/16
```

not:

```text
0.0.0.0/0
```

So we're **not exposing MySQL directly to the Internet**.

---

# 6. Create the RDS subnet group

Open:

```bash
nano rds.tf
```

Add:

```hcl
resource "aws_db_subnet_group" "mysql" {
  name = "${var.project_name}-${var.environment}-mysql-subnet-group"

  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${var.project_name}-${var.environment}-mysql-subnet-group"
  }
}
```

Our database will therefore live in:

```text
Private Subnet 1
Private Subnet 2
```

---

# 7. Create RDS MySQL

Continue in `rds.tf`:

```hcl
resource "aws_db_instance" "mysql" {
  identifier = "${var.project_name}-${var.environment}-mysql"

  engine         = "mysql"
  engine_version = "8.0"

  instance_class = "db.t3.micro"

  allocated_storage     = 20
  max_allocated_storage = 50
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password
  port     = 3306

  db_subnet_group_name = aws_db_subnet_group.mysql.name

  vpc_security_group_ids = [
    aws_security_group.rds.id
  ]

  publicly_accessible = false

  multi_az = false

  backup_retention_period = 7

  deletion_protection = false

  skip_final_snapshot = true

  auto_minor_version_upgrade = true

  apply_immediately = true

  tags = {
    Name = "${var.project_name}-${var.environment}-mysql"
  }
}
```

For our DevOps lab, we're using:

```text
db.t3.micro
20 GB
Single-AZ
Private
Encrypted
```

This keeps the development environment simpler and cheaper than a production HA database.

---

# 8. Add RDS outputs

Open:

```bash
nano outputs.tf
```

Append:

```hcl
output "rds_endpoint" {
  description = "RDS MySQL endpoint"
  value       = aws_db_instance.mysql.address
}

output "rds_port" {
  description = "RDS MySQL port"
  value       = aws_db_instance.mysql.port
}

output "rds_database_name" {
  description = "RDS database name"
  value       = aws_db_instance.mysql.db_name
}
```

Don't output the password.

---

# 9. Format Terraform

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

---

# 10. Check the plan

Run:

```bash
terraform plan
```

Review carefully.

Terraform should now understand:

```text
VPC
├── Public subnets
├── Private subnets
├── Internet Gateway
├── NAT Gateway
│
├── ECR
│   ├── frontend
│   └── backend
│
├── RDS
│   ├── Subnet Group
│   └── MySQL
│
└── Security Group
    └── RDS
```

---

# 11. Apply the ECR + RDS configuration

If the plan is correct:

```bash
terraform apply
```

Enter:

```text
yes
```

RDS creation can take several minutes.

Don't worry if you see:

```text
Still creating...
```

for a while.

---

# 12. Check Terraform outputs

After completion:

```bash
terraform output
```

You should eventually have something similar to:

```text
backend_ecr_repository_url = "ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/aws-community-backend"

frontend_ecr_repository_url = "ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/aws-community-frontend"

rds_database_name = "aws_community"

rds_endpoint = "aws-community-dev-mysql.xxxxxxxxx.ap-south-1.rds.amazonaws.com"

rds_port = 3306

private_subnet_ids = [...]
public_subnet_ids = [...]

vpc_id = "vpc-xxxxxxxx"
```

---

# 13. Verify RDS directly through AWS CLI

Run:

```bash
aws rds describe-db-instances \
  --db-instance-identifier aws-community-dev-mysql \
  --region ap-south-1 \
  --query 'DBInstances[0].{Status:DBInstanceStatus,Endpoint:Endpoint.Address,Port:Endpoint.Port,Public:PubliclyAccessible}' \
  --output table
```

You want:

```text
Status      available
Public      False
Port        3306
```

The important part is:

```text
Public: False
```

---

# 14. Verify ECR

```bash
aws ecr describe-repositories \
  --region ap-south-1 \
  --query 'repositories[].{Name:repositoryName,URI:repositoryUri}' \
  --output table
```

You should have:

```text
aws-community-backend
aws-community-frontend
```

---

# 15. Important: our application is changing

Before RDS:

```text
Docker
│
├── Frontend
├── Backend
└── MySQL
```

Now:

```text
EC2 / Docker
│
├── Frontend
└── Backend
       |
       v
      RDS
       |
       v
   MySQL 8.0
```

And eventually:

```text
                    AWS
                     |
               Application LB
                     |
                    EKS
                ┌────┴────┐
                │         │
           Frontend      Backend
                           |
                           |
                           v
                       RDS MySQL
```

---

# 16. One thing we should NOT do yet

Don't change your Docker Compose database immediately.

We'll keep:

```text
docker-compose.yml
       |
       v
local MySQL container
```

for local development.

For Kubernetes:

```text
EKS
 |
 v
Backend
 |
 v
RDS
```

We'll inject the RDS endpoint/password into Kubernetes using:

```text
Kubernetes Secret
```

So we'll have two environments:

```text
Development

Docker Compose
    |
    └── MySQL container


AWS

EKS
 |
 └── RDS MySQL
```

That's a much cleaner DevOps architecture.

---

# Phase 3.2 completion checklist

After successful `terraform apply`:

```text
Phase 3.2 — ECR + RDS
──────────────────────────────

[✓] ECR frontend repository
[✓] ECR backend repository
[✓] ECR image scanning
[✓] ECR encryption
[✓] RDS subnet group
[✓] RDS security group
[✓] RDS MySQL
[✓] RDS private access
[✓] RDS encryption
[✓] Terraform outputs
```

## Next: Phase 3.3 — IAM + EKS

Then we'll create the Kubernetes infrastructure:

```text
Terraform
   |
   ├── EKS Cluster IAM
   ├── EKS Node IAM
   ├── EKS Cluster
   ├── Managed Node Group
   └── EKS networking
             |
             v
           EKS
       ┌─────┴─────┐
       │           │
   Frontend     Backend
                   |
                   v
                  RDS
```

**Before moving to EKS, run `terraform plan` and `terraform apply`, then send me the output of:**

```bash
terraform output
```

and:

```bash
aws rds describe-db-instances \
  --db-instance-identifier aws-community-dev-mysql \
  --region ap-south-1 \
  --query 'DBInstances[0].{Status:DBInstanceStatus,Endpoint:Endpoint.Address,Public:PubliclyAccessible}' \
  --output table
```

That will let us verify the infrastructure before we create EKS.
