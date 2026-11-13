variable "aws_region" {
  description = "AWS Region used for the lab."
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Short name used in AWS resource names and tags."
  type        = string
  default     = "cloudops-guard"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,19}$", var.project_name))
    error_message = "project_name must be 3-20 lowercase letters, numbers, or hyphens and start with a letter."
  }
}

variable "instance_type" {
  description = "Small EC2 instance type for the demo. Check current regional pricing before applying."
  type        = string
  default     = "t3.micro"
}

variable "vpc_cidr" {
  description = "CIDR block for the isolated lab VPC."
  type        = string
  default     = "10.40.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for the single public subnet."
  type        = string
  default     = "10.40.1.0/24"
}

variable "github_oidc_subject" {
  description = "Exact GitHub OIDC subject allowed to deploy. Default is scoped to this repository's main branch and its immutable account/repository IDs."
  type        = string
  default     = "repo:dk7538456-bot@293495808/cloudops-aws-devops-project@1373073270:ref:refs/heads/main"
}

variable "alarm_topic_arn" {
  description = "Optional SNS topic ARN for instance status-check alarm notifications."
  type        = string
  default     = ""
}
