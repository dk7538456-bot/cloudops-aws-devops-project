# CloudOps Delivery Guard

An AWS deployment project for a small status service. It combines Terraform, Docker, GitHub Actions, IAM OIDC, Systems Manager, and a local Terraform-plan guardrail in one reproducible workflow.

The project is designed for a student lab: it uses one small public EC2 instance and no NAT Gateway. GitHub Actions receives short-lived AWS credentials through OIDC. The instance has no SSH ingress; deploys run through Systems Manager Run Command.

## Why this project stands out

- **No stored AWS access keys:** the deploy workflow assumes a narrowly scoped IAM role using GitHub OIDC.
- **No public SSH:** the instance is managed through Systems Manager.
- **Plan review before apply:** `scripts/guardrail.py` flags common risky Terraform changes, including open SSH, public databases, unencrypted storage, and wildcard IAM policies.
- **Infrastructure as Code:** Terraform creates a VPC, public subnet, security group, EC2 instance profile, ECR repository, deployment role, and CloudWatch alarm.
- **Container hardening:** the service runs as a non-root user with a read-only container filesystem and health endpoint.
- **Manual production deploy:** CI validates on pushes and pull requests; the AWS deployment workflow runs only when manually requested.

## Architecture

```text
Pull request / push
  └─ GitHub Actions: Python compile + Docker build + Terraform fmt/validate + plan guardrail example

Manual deploy
  └─ GitHub Actions --OIDC--> AWS IAM role
       ├─ Build image --> Amazon ECR
       └─ Systems Manager Run Command --> EC2 pulls image and replaces container

Browser --> EC2:80 --> container:5000
                   └─ /health and /api/status
```

The instance is in a single public subnet so it can reach ECR and Systems Manager without a NAT Gateway. Only HTTP port 80 is inbound by default. This is a learning deployment; use HTTPS through an Application Load Balancer or CloudFront before serving real users.

## Repository map

- `app/` — Flask status service.
- `Dockerfile`, `docker-compose.yml` — local container and hardened runtime settings.
- `main.tf`, `iam.tf`, `variables.tf`, `outputs.tf` — AWS infrastructure.
- `.github/workflows/ci.yml` — validation on pull requests and pushes.
- `.github/workflows/deploy.yml` — manual OIDC/ECR/SSM deployment.
- `scripts/guardrail.py` — standard-library Terraform plan JSON scanner.
- `guardrail/examples/` — sample safe and unsafe plan JSON.

## Run locally

Requirements: Docker Desktop or Docker Engine with Compose.

```bash
docker compose up --build
```

Open `http://localhost:8080`. Health check: `http://localhost:8080/health`.

Stop the service:

```bash
docker compose down
```

## Check a Terraform plan

```bash
terraform init
terraform plan -out=tfplan
terraform show -json tfplan > plan.json
python scripts/guardrail.py plan.json --fail-on high
```

The scanner also accepts the included examples:

```bash
python scripts/guardrail.py guardrail/examples/safe-plan.json --fail-on high
python scripts/guardrail.py guardrail/examples/unsafe-plan.json --format json --fail-on high
```

The scanner is a focused teaching tool, not a replacement for a full cloud security review. It checks resource attributes present in Terraform plan JSON; unknown values and resources outside its rules may need manual review.

## Deploy to AWS

### 1. Prerequisites

- An AWS account or sandbox where you can create EC2, VPC, ECR, IAM, Systems Manager, and CloudWatch resources.
- Terraform 1.11 or later, AWS CLI v2, Docker, and GitHub Actions enabled for this repository.
- An existing default VPC is **not** required; Terraform creates a small VPC and one public subnet.
- Review AWS pricing before applying. EC2, the public IPv4 address, EBS, ECR storage, and network transfer can cost money.

### 2. Configure GitHub OIDC in AWS

Create the GitHub OIDC identity provider once per AWS account if it does not already exist:

- Provider URL: `https://token.actions.githubusercontent.com`
- Audience: `sts.amazonaws.com`

The Terraform deployment role trusts only this repository's `main` branch. The default subject uses the current immutable GitHub owner/repository IDs. If GitHub shows a different subject claim for your workflow, set `github_oidc_subject` in `terraform.tfvars` to that exact subject.

### 3. Create infrastructure

```bash
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan -out=tfplan
terraform show -json tfplan > plan.json
python scripts/guardrail.py plan.json --fail-on high
terraform apply tfplan
```

If your shell does not support process substitution, save the plan JSON to a file and pass that file to the guardrail command.

Copy the Terraform outputs into GitHub repository **Variables** (Settings → Secrets and variables → Actions → Variables):

- `AWS_ROLE_ARN` ← `github_actions_role_arn`
- `AWS_REGION` ← `aws_region`
- `ECR_REPOSITORY` ← `ecr_repository_name`
- `EC2_INSTANCE_ID` ← `instance_id`

No AWS access key or SSH private key is needed in GitHub.

### 4. Deploy

In GitHub, open **Actions → Deploy to EC2 through SSM → Run workflow**. The workflow builds an image tagged with the commit SHA, pushes it to ECR, and asks Systems Manager to deploy it. When the workflow succeeds, open the `service_url` Terraform output.

### 5. Clean up

```bash
terraform destroy
```

Confirm the stack is removed in the AWS console. ECR images may need to be deleted separately if the repository is retained.

## Security and operational notes

- The Terraform default has no SSH rule and does not expose container port 5000.
- The EC2 root volume is encrypted, IMDSv2 is required, and the instance role only has SSM management plus ECR image-pull permissions.
- The GitHub deploy role is restricted to a single repository and branch, and can push only to its ECR repository and send SSM commands to the tagged lab instance.
- The demo serves HTTP directly from EC2 and contains no user data. Do not add secrets or personal information to it.
- Terraform state is local by default. For team use, configure a protected remote backend with locking and encryption.
- No AWS resources are created by CI. The deploy workflow is manual and runs only after AWS setup.

## Resume-ready wording

Use only after you have followed the deployment guide and confirmed the workflow in your own AWS account:

> Built a Terraform-managed AWS deployment for a containerized Python service, using GitHub Actions OIDC for short-lived AWS access, ECR for immutable image releases, and Systems Manager for SSH-less deployment; added plan-time guardrails for public ingress, encryption, and IAM risks.

## License

MIT.
