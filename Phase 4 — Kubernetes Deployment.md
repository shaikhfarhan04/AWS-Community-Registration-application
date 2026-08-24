Absolutely. Now we move to **Phase 4 — Kubernetes Deployment**.

Our goal is to deploy the Docker images from **ECR → EKS**, connect the backend to **RDS MySQL**, and expose the frontend through an AWS Load Balancer.

### Phase 4 architecture

```text
                         Internet
                            │
                            ▼
                 AWS Load Balancer
                            │
                            ▼
                    Frontend Service
                            │
                            ▼
                     Frontend Pods
                            │
                     API requests
                            ▼
                     Backend Service
                            │
                            ▼
                     Backend Pods
                            │
                            │ TCP 3306
                            ▼
                       RDS MySQL


ECR
├── aws-community-frontend:latest
└── aws-community-backend:latest

EKS
├── Namespace
├── ConfigMap
├── Secret
├── Frontend Deployment
├── Frontend Service
├── Backend Deployment
└── Backend Service
```

We will do this in small steps so that if something fails, we know exactly where.

---

# Phase 4.1 — Verify EKS

First:

```bash
cd ~/AWS-Community-Registration-application
```

Check the cluster:

```bash
aws eks list-clusters --region ap-south-1
```

Then:

```bash
kubectl config current-context
```

And:

```bash
kubectl get nodes
```

You should see nodes in:

```text
Ready
```

For example:

```text
NAME                          STATUS   ROLES
ip-10-0-10-xxx.ec2.internal   Ready    <none>
ip-10-0-11-xxx.ec2.internal   Ready    <none>
```

If the nodes aren't `Ready`, **stop here** and fix EKS first.

---

# Phase 4.2 — Create Kubernetes directory

From your project:

```bash
mkdir -p k8s
cd k8s
```

Create:

```bash
touch namespace.yaml
touch configmap.yaml
touch secret.yaml
touch backend-deployment.yaml
touch backend-service.yaml
touch frontend-deployment.yaml
touch frontend-service.yaml
```

Later we'll add the AWS Load Balancer/Ingress configuration.

Your structure becomes:

```text
AWS-Community-Registration-application/
│
├── backend/
├── frontend/
├── terraform/
│
├── k8s/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── backend-deployment.yaml
│   ├── backend-service.yaml
│   ├── frontend-deployment.yaml
│   └── frontend-service.yaml
│
└── docker-compose.yml
```

---

# Phase 4.3 — Kubernetes namespace

Open:

```bash
nano namespace.yaml
```

Add:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: aws-community
```

Apply:

```bash
kubectl apply -f namespace.yaml
```

Verify:

```bash
kubectl get namespaces
```

You should see:

```text
aws-community
```

---

# Phase 4.4 — RDS configuration

Now we need to give the backend the RDS information.

First retrieve the RDS endpoint:

```bash
cd ../terraform
terraform output -raw rds_endpoint
```

It should return something similar to:

```text
aws-community-dev-mysql.xxxxx.ap-south-1.rds.amazonaws.com
```

Save it temporarily:

```bash
export RDS_ENDPOINT=$(terraform output -raw rds_endpoint)
```

Verify:

```bash
echo $RDS_ENDPOINT
```

---

# Phase 4.5 — Kubernetes ConfigMap

Go back:

```bash
cd ../k8s
```

Open:

```bash
nano configmap.yaml
```

Use:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-community-config
  namespace: aws-community
data:
  DB_HOST: "REPLACE_RDS_ENDPOINT"
  DB_PORT: "3306"
  DB_NAME: "aws_community"
```

Replace:

```text
REPLACE_RDS_ENDPOINT
```

with your actual RDS endpoint.

For example:

```yaml
DB_HOST: "aws-community-dev-mysql.xxxxx.ap-south-1.rds.amazonaws.com"
```

Apply:

```bash
kubectl apply -f configmap.yaml
```

Verify:

```bash
kubectl get configmap -n aws-community
```

---

# Phase 4.6 — Kubernetes Secret

We don't want the database password inside the ConfigMap.

Open:

```bash
nano secret.yaml
```

Use:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: aws-community-db-secret
  namespace: aws-community
type: Opaque
stringData:
  DB_USER: "community_app"
  DB_PASSWORD: "REPLACE_WITH_YOUR_RDS_PASSWORD"
```

Replace:

```text
REPLACE_WITH_YOUR_RDS_PASSWORD
```

with the same password used when you created the RDS instance.

Then:

```bash
kubectl apply -f secret.yaml
```

Check:

```bash
kubectl get secrets -n aws-community
```

**Do not commit this file to GitHub.**

Add this to your project's `.gitignore`:

```text
k8s/secret.yaml
```

---

# Phase 4.7 — Backend Deployment

Now we'll deploy the Flask API.

Open:

```bash
nano backend-deployment.yaml
```

Use:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: aws-community
spec:
  replicas: 2

  selector:
    matchLabels:
      app: backend

  template:
    metadata:
      labels:
        app: backend

    spec:
      containers:
        - name: backend

          image: ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/aws-community-backend:latest

          ports:
            - containerPort: 5000

          env:
            - name: DB_HOST
              valueFrom:
                configMapKeyRef:
                  name: aws-community-config
                  key: DB_HOST

            - name: DB_PORT
              valueFrom:
                configMapKeyRef:
                  name: aws-community-config
                  key: DB_PORT

            - name: DB_NAME
              valueFrom:
                configMapKeyRef:
                  name: aws-community-config
                  key: DB_NAME

            - name: DB_USER
              valueFrom:
                secretKeyRef:
                  name: aws-community-db-secret
                  key: DB_USER

            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: aws-community-db-secret
                  key: DB_PASSWORD

          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"

            limits:
              cpu: "500m"
              memory: "512Mi"
```

Replace:

```text
ACCOUNT_ID
```

with your AWS account ID.

Get it with:

```bash
aws sts get-caller-identity \
  --query Account \
  --output text
```

---

# Phase 4.8 — Backend Service

Open:

```bash
nano backend-service.yaml
```

Use:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: aws-community
spec:
  type: ClusterIP

  selector:
    app: backend

  ports:
    - port: 5000
      targetPort: 5000
      protocol: TCP
```

This means the backend is **not directly exposed to the Internet**.

```text
Frontend
   │
   ▼
Backend Service
   │
   ▼
Backend Pods
```

---

# Phase 4.9 — Deploy backend

Apply:

```bash
kubectl apply -f backend-deployment.yaml
kubectl apply -f backend-service.yaml
```

Check:

```bash
kubectl get deployments -n aws-community
```

Then:

```bash
kubectl get pods -n aws-community
```

Expected:

```text
NAME                       READY
backend-xxxxxxxxx-xxxxx    1/1
backend-xxxxxxxxx-xxxxx    1/1
```

Check service:

```bash
kubectl get svc -n aws-community
```

Expected:

```text
backend    ClusterIP
```

---

# Phase 4.10 — Check backend logs

Run:

```bash
kubectl logs -n aws-community deployment/backend
```

This is very important.

We want to see your Flask application start successfully.

If you get:

```text
Access denied for user
```

then we'll fix the RDS credentials.

If you get:

```text
Can't connect to MySQL server
```

then we'll check the RDS security group/networking.

---

# Phase 4.11 — Test backend inside Kubernetes

Run:

```bash
kubectl run curl-test \
  -n aws-community \
  --image=curlimages/curl \
  --rm -it \
  --restart=Never \
  -- curl http://backend:5000/api/health
```

Your Flask health endpoint should return something similar to:

```json
{
  "status": "ok"
}
```

or your application's database health response.

This proves:

```text
Kubernetes
   │
   ▼
Backend Pod
   │
   ▼
RDS MySQL
```

---

# Phase 4.12 — Frontend Deployment

Now we'll deploy your frontend.

Open:

```bash
nano frontend-deployment.yaml
```

Use:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: aws-community
spec:
  replicas: 2

  selector:
    matchLabels:
      app: frontend

  template:
    metadata:
      labels:
        app: frontend

    spec:
      containers:
        - name: frontend

          image: ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/aws-community-frontend:latest

          ports:
            - containerPort: 80

          resources:
            requests:
              cpu: "100m"
              memory: "64Mi"

            limits:
              cpu: "300m"
              memory: "256Mi"
```

Again replace:

```text
ACCOUNT_ID
```

with your account ID.

---

# Phase 4.13 — Frontend Service

Open:

```bash
nano frontend-service.yaml
```

For our first deployment, use:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: aws-community
spec:
  type: LoadBalancer

  selector:
    app: frontend

  ports:
    - port: 80
      targetPort: 80
      protocol: TCP
```

This will ask AWS to provision an external Load Balancer.

---

# Phase 4.14 — Deploy frontend

Run:

```bash
kubectl apply -f frontend-deployment.yaml
kubectl apply -f frontend-service.yaml
```

Check:

```bash
kubectl get pods -n aws-community
```

Then:

```bash
kubectl get svc -n aws-community
```

You should eventually see:

```text
NAME       TYPE           EXTERNAL-IP
backend    ClusterIP      ...
frontend   LoadBalancer   ...
```

The Load Balancer may initially show:

```text
<pending>
```

Give AWS a few minutes.

Then:

```bash
kubectl get svc frontend \
  -n aws-community \
  -w
```

Once the external hostname appears, press:

```text
Ctrl+C
```

---

# Phase 4.15 — Get application URL

Run:

```bash
kubectl get svc frontend \
  -n aws-community \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

You'll get something similar to:

```text
a1234567890abcdef.elb.amazonaws.com
```

Open that hostname in your browser.

You should see your:

```text
AWS Community Registration
```

form.

---

# Phase 4.16 — Verify the entire application

Our final request path is now:

```text
Browser
   │
   ▼
AWS Load Balancer
   │
   ▼
Frontend Service
   │
   ▼
Frontend Pod
   │
   ▼
Backend Service
   │
   ▼
Flask Backend
   │
   ▼
RDS MySQL
```

When you submit:

```text
Name
Email
Phone
Company
etc.
```

the request should reach:

```text
/api/register
```

and eventually:

```text
RDS MySQL
```

---

# Important: frontend → backend URL

There is one application-specific point we need to verify.

Your frontend must not call:

```text
http://localhost:5000/api/register
```

inside Kubernetes.

`localhost` inside a frontend container means **the frontend container itself**.

Instead, Kubernetes communication should use the backend Service:

```text
http://backend:5000/api/register
```

However, if your frontend is a browser-side JavaScript application, the browser cannot directly resolve the Kubernetes service name `backend`.

In that case, we'll use **Nginx as a reverse proxy**:

```text
Browser
   |
   v
Load Balancer
   |
   v
Nginx / Frontend
   |
   | /api/*
   v
backend:5000
```

That is actually the cleaner architecture for your project.

So **don't change your frontend API URL yet** if your current Docker setup already uses Nginx. We'll inspect the existing frontend/Nginx configuration before finalizing it.

---

# Phase 4 checklist

```text
Phase 4 — Kubernetes
────────────────────────────

[ ] EKS cluster verified
[ ] Namespace created
[ ] RDS ConfigMap created
[ ] DB Secret created
[ ] Backend Deployment
[ ] Backend Service
[ ] Backend → RDS tested
[ ] Frontend Deployment
[ ] Frontend Service
[ ] Load Balancer created
[ ] Registration form accessible
[ ] Registration saved to RDS
```

### Do this first

Don't apply everything at once.

Run:

```bash
kubectl get nodes
```

Then:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml
```

Then:

```bash
kubectl get pods -n aws-community
kubectl get svc -n aws-community
kubectl logs -n aws-community deployment/backend
```

**Once the backend pods are `Running` and the logs show Flask started successfully, we'll proceed with the frontend + Nginx + AWS Load Balancer.**
