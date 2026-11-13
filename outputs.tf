output "aws_region" {
  description = "Region configured for this lab."
  value       = var.aws_region
}

output "instance_id" {
  description = "EC2 instance targeted by the manual SSM deployment workflow."
  value       = aws_instance.app.id
}

output "service_url" {
  description = "HTTP URL for the demo service. Add HTTPS in front before serving real users."
  value       = "http://${aws_instance.app.public_ip}"
}

output "ecr_repository_name" {
  description = "ECR repository name used by the deployment workflow."
  value       = aws_ecr_repository.app.name
}

output "ecr_repository_url" {
  description = "Full ECR repository URL."
  value       = aws_ecr_repository.app.repository_url
}

output "github_actions_role_arn" {
  description = "IAM role assumed by the repository's GitHub Actions deploy workflow."
  value       = aws_iam_role.github_deploy.arn
}
