# Infrastructure as Code (IaC) — Agentic Hybrid RAG System

This directory contains the modular **Terraform** configuration defining the future AWS cloud infrastructure for the **Agentic Hybrid RAG** Python application (`config/`, `core/`, `database/`).

> **Note:** Cloud deployment is **not** required for Task 6. `offline_plan_mode = true` is enabled by default so `terraform init`, `terraform validate`, and `terraform plan` execute cleanly without an AWS account or live credentials. Do **not** run `terraform apply` unless you intend to provision real AWS resources.

---

## Infrastructure Design

The application runs a 3-agent LangGraph/LangChain pipeline (**Retriever → Analyst → Answer**) backed by **ChromaDB**, **SentenceTransformers** (`all-MiniLM-L6-v2` & `ms-marco-MiniLM-L-6-v2`), **RapidOCR**, **Faster-Whisper**, **OpenRouter**, and **Redis/Memurai** caching (`config/settings.py`).

```
Client ──▶ Application Load Balancer (Public Subnets)
                 │
                 ▼
         ECS Fargate Tasks (Private Subnets)
           ├──▶ Amazon EFS (/app/chroma_db, /app/uploads/images)
           ├──▶ ElastiCache Redis (Port 6379 — retrieval/response/semantic cache)
           ├──▶ Amazon S3 (Encrypted raw documents & knowledge-base archive)
           ├──▶ Secrets Manager (OPENROUTER_API_KEY, REDIS_PASSWORD)
           └──▶ NAT Gateway ──▶ OpenRouter API / HuggingFace / Web Loaders
```

### Directory Structure

```text
terraform/
├── providers.tf               # Terraform >= 1.5 & AWS ~> 5.0 provider + offline plan toggle
├── main.tf                    # Root module wiring networking, storage, security, cache, compute
├── variables.tf               # Typed, validated input variables
├── outputs.tf                 # Key infrastructure outputs (VPC, ECR, ECS, ALB, EFS, S3, Redis)
├── terraform.tfvars.example   # Safe non-secret example variable overrides
├── .gitignore                 # Ignores .terraform/, state files, plans, and secret tfvars
├── README.md                  # This documentation
└── modules/
    ├── networking/            # VPC, 2 public + 2 private subnets, IGW, NAT GW, route tables, SGs
    ├── storage/               # S3 bucket (versioned + SSE-AES256) + EFS with Chroma & upload APs
    ├── security/              # IAM execution/task roles + Secrets Manager secrets
    ├── cache/                 # ElastiCache Redis replication group & subnet group
    └── compute/               # ECR repository, CloudWatch logs, ALB, ECS cluster/task/service
```

---

## Variables

### Core Configuration

| Variable | Type | Default | Description |
|---|---|---|---|
| `project_name` | `string` | `"hybrid-rag"` | Short lowercase identifier (`3-18` chars) used as resource name prefix |
| `environment` | `string` | `"dev"` | Target environment (`dev`, `staging`, or `prod`) |
| `aws_region` | `string` | `"us-east-1"` | Target AWS region |
| `offline_plan_mode` | `bool` | `true` | Enables credential-free `terraform plan`; set to `false` for real AWS deployments |

### Networking, Compute, Storage & Cache

| Variable | Type | Default | Description |
|---|---|---|---|
| `vpc_cidr` | `string` | `"10.0.0.0/16"` | Dedicated VPC CIDR block |
| `availability_zones` | `list(string)` | `["us-east-1a", "us-east-1b"]` | Two AZs for multi-AZ subnet placement |
| `public_subnet_cidrs` | `list(string)` | `["10.0.1.0/24", "10.0.2.0/24"]` | Public subnets for ALB and NAT Gateway |
| `private_subnet_cidrs` | `list(string)` | `["10.0.11.0/24", "10.0.12.0/24"]` | Private subnets for ECS, EFS, and Redis |
| `enable_nat_gateway` | `bool` | `true` | Outbound internet access for OpenRouter API & web loaders |
| `container_port` | `number` | `8000` | Application container TCP port |
| `container_image_tag` | `string` | `"latest"` | Docker image tag in ECR |
| `ecs_task_cpu` | `number` | `2048` | Fargate CPU units (`2048` = 2 vCPU) |
| `ecs_task_memory` | `number` | `4096` | Fargate memory in MiB |
| `desired_count` | `number` | `1` | Desired running ECS Fargate task count |
| `llm_model` | `string` | `"openrouter/free"` | Maps to `LLM_MODEL` in `config/settings.py` |
| `embedding_device` | `string` | `"cpu"` | Embedding device (`cpu` or `cuda`) |
| `redis_node_type` | `string` | `"cache.t3.small"` | ElastiCache Redis node size |
| `redis_port` | `number` | `6379` | Maps to `REDIS_PORT` in `config/settings.py` |
| `redis_db` | `number` | `0` | Maps to `REDIS_DB` in `config/settings.py` |
| `efs_performance_mode` | `string` | `"generalPurpose"` | EFS mode (`generalPurpose` or `maxIO`) |
| `enable_s3_versioning` | `bool` | `true` | Enables S3 object versioning for uploaded documents |

### Sensitive Variables (Never Commit to Git)

| Variable | Sensitive | Description |
|---|---|---|
| `openrouter_api_key` | Yes | Stored in AWS Secrets Manager (`OPENROUTER_API_KEY`); leave `""` for offline plan |
| `redis_auth_token` | Yes | Stored in AWS Secrets Manager (`REDIS_PASSWORD`); leave `""` for offline plan |

---

## How to Initialize, Validate, and Plan

Run the following commands from the project root (or inside `terraform/` without `-chdir=terraform`):

1. **Format check**
   ```powershell
   terraform -chdir=terraform fmt -check -recursive
   ```
2. **Initialize providers and local modules**
   ```powershell
   terraform -chdir=terraform init
   ```
3. **Validate configuration syntax and module wiring**
   ```powershell
   terraform -chdir=terraform validate
   ```
4. **Generate an offline execution plan (dry-run)**
   ```powershell
   terraform -chdir=terraform plan
   ```

### Future Real Cloud Deployment (Optional)

When ready to deploy to an actual AWS account:
1. Configure AWS CLI credentials (`aws configure` or environment variables).
2. Pass secrets safely via environment variables:
   ```powershell
   $env:TF_VAR_offline_plan_mode  = "false"
   $env:TF_VAR_openrouter_api_key = "<your-openrouter-api-key>"
   $env:TF_VAR_redis_auth_token   = "<your-16+-char-redis-token>"
   ```
3. Run `terraform -chdir=terraform plan` and review carefully before applying.
