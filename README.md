# CloudOps Demo: Docker + AWS EC2 + Terraform + GitHub Actions

A fresher-friendly Cloud/DevOps project designed around the skills requested in the VLSI Technology Cloud/DevOps Engineer JD: cloud infrastructure, Linux, CI/CD, Docker, Terraform/IaC, monitoring concepts, troubleshooting and documentation.

## What this project demonstrates

- AWS EC2 cloud infrastructure
- Linux server administration
- Docker containerization
- Docker Compose
- Terraform Infrastructure as Code
- Git/GitHub version control
- GitHub Actions CI pipeline
- Optional EC2 deployment workflow
- Health endpoint for basic operational monitoring
- Basic security-group/access-control concepts

## Architecture

Developer -> GitHub -> GitHub Actions (test + Docker build) -> EC2 -> Docker Container -> Flask App
                                      |
                                      +-> Terraform provisions EC2 + Security Group

## Local run

Requirements: Docker Desktop

```bash
docker compose up -d --build
```

Open:
- http://localhost:5000
- http://localhost:5000/health

Stop:
```bash
docker compose down
```

## Run tests

```bash
pip install -r app/requirements.txt
cd app
pytest -q
```

## AWS/Terraform deployment

1. Create an AWS account and an EC2 key pair.
2. Install Terraform and configure AWS credentials locally. Never commit credentials.
3. Copy `terraform/terraform.tfvars.example` to `terraform/terraform.tfvars`.
4. Put your existing EC2 key pair name in `terraform.tfvars`.
5. From the `terraform` directory:

```bash
terraform init
terraform plan
terraform apply
```

6. Terraform prints the EC2 public IP and health URL.
7. SSH to the instance and verify Docker:

```bash
ssh -i YOUR_KEY.pem ubuntu@PUBLIC_IP
docker --version
```

> Cost note: AWS resources can incur charges. Destroy the infrastructure when finished:
```bash
terraform destroy
```

## GitHub Actions

`ci.yml` runs automatically on pushes/PRs to `main`:
1. Checkout
2. Install Python dependencies
3. Run pytest
4. Build Docker image

`deploy.yml` is manual (`workflow_dispatch`). To use it, configure these GitHub repository secrets:
- `EC2_HOST`
- `EC2_USER` (normally `ubuntu` for the Ubuntu AMI)
- `EC2_SSH_KEY` (private SSH key content)

Then run the **Deploy to EC2** workflow from the GitHub Actions tab.

## Interview explanation — 60 seconds

"I built a small CloudOps deployment project to understand the complete flow from code to cloud deployment. The application is a simple Flask service with a health endpoint. I containerized it using Docker, used Terraform to provision an AWS EC2 instance and security group, and used GitHub Actions for automated testing and Docker image building. I also added a manual deployment workflow that copies the application to EC2 and starts it with Docker Compose. The project helped me understand Linux administration, cloud networking, IAM/security concepts, containerization, CI/CD and Infrastructure as Code."

## Likely interview questions

1. Why did you choose EC2?
2. What is a security group?
3. Why use Docker?
4. Image vs container?
5. What is Docker Compose?
6. What is Terraform and why use IaC?
7. What happens during `terraform plan` and `terraform apply`?
8. What is CI/CD?
9. Why GitHub Actions?
10. How does the workflow deploy to EC2?
11. Why should secrets not be stored in Git?
12. How would you monitor this application in production?
13. How would you make the application highly available?
14. How would you restrict SSH access?
15. What would you do if the container keeps restarting?
16. How would you troubleshoot a 502/connection error?
17. What is the purpose of the `/health` endpoint?
18. How would you scale this application?

## Important security improvements to mention

For a real production environment, I would:
- Restrict SSH (port 22) to a trusted IP or use AWS Systems Manager.
- Avoid exposing port 5000 publicly and place the app behind an Nginx/load balancer.
- Store secrets in GitHub Actions Secrets / AWS Secrets Manager.
- Use least-privilege IAM policies.
- Add HTTPS/TLS.
- Add CloudWatch metrics/logs and alerts.
- Use private subnets where appropriate.
- Add backups and disaster-recovery planning.

## Resume rule

Do not claim this project as completed until you have run it locally and, ideally, deployed it once. After you verify it, use the project bullets from the tailored resume supplied with this package.
