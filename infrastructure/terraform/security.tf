# Security Groups already defined in main.tf

# AWS WAF for basic protection
resource "aws_wafv2_web_acl" "main" {
  name        = "formiq-waf"
  description = "WAF for FormIQ application"
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  # Block common web attacks
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesCommonRuleSet"
      sampled_requests_enabled   = true
    }
  }

  # Rate limiting
  rule {
    name     = "RateLimitRule"
    priority = 2

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 2000 # Requests per 5 minutes
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimitRule"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "formiq-waf"
    sampled_requests_enabled   = true
  }
}

# S3 bucket policy for secure access
resource "aws_s3_bucket_policy" "video_storage" {
  bucket = aws_s3_bucket.video_storage.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Deny"
        Principal = "*"
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.video_storage.arn,
          "${aws_s3_bucket.video_storage.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

# Server-side encryption for S3 buckets
resource "aws_s3_bucket_server_side_encryption_configuration" "video_storage" {
  bucket = aws_s3_bucket.video_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# IAM role for EC2 instance
resource "aws_iam_role" "ec2_role" {
  name = "formiq-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

# IAM policy for S3 access
resource "aws_iam_policy" "s3_access" {
  name        = "formiq-s3-access"
  description = "Allow access to FormIQ S3 buckets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
          "s3:DeleteObject"
        ]
        Effect = "Allow"
        Resource = [
          aws_s3_bucket.video_storage.arn,
          "${aws_s3_bucket.video_storage.arn}/*",
          aws_s3_bucket.frontend_assets.arn,
          "${aws_s3_bucket.frontend_assets.arn}/*"
        ]
      }
    ]
  })
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "s3_access" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.s3_access.arn
}

# EC2 instance profile
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "formiq-ec2-profile"
  role = aws_iam_role.ec2_role.name
}

# Update EC2 instance to use the IAM role
resource "aws_instance" "backend" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.medium"
  subnet_id     = module.vpc.public_subnets[0]
  
  vpc_security_group_ids = [aws_security_group.backend.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name
  
  tags = {
    Name        = "formiq-backend"
    Environment = var.environment
    Project     = "formiq"
  }
}

# WAF Web ACL Association
resource "aws_wafv2_web_acl_association" "main" {
  resource_arn = aws_lb.main.arn
  web_acl_arn  = aws_wafv2_web_acl.main.arn
}

# AWS Shield
resource "aws_shield_protection" "main" {
  name         = "formiq-shield"
  resource_arn = aws_lb.main.arn

  tags = {
    Environment = var.environment
    Project     = "formiq"
  }
}

# KMS Key for Secrets
resource "aws_kms_key" "secrets" {
  description             = "KMS key for FormIQ secrets"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = {
    Environment = var.environment
    Project     = "formiq"
  }
}

# KMS Key Alias
resource "aws_kms_alias" "secrets" {
  name          = "alias/formiq-secrets"
  target_key_id = aws_kms_key.secrets.key_id
}

# Secrets Manager for Database Password
resource "aws_secretsmanager_secret" "db_password" {
  name = "formiq/db-password"

  tags = {
    Environment = var.environment
    Project     = "formiq"
  }
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = var.db_password

  lifecycle {
    ignore_changes = [
      secret_string
    ]
  }
}

# Security Hub
resource "aws_securityhub_account" "main" {
  control_finding_generator = "SECURITY_CONTROL"
  auto_enable_controls     = true
}

# GuardDuty
resource "aws_guardduty_detector" "main" {
  enable = true

  datasources {
    s3_logs {
      enable = true
    }
    kubernetes {
      audit_logs {
        enable = true
      }
    }
    malware_protection {
      scan_ec2_instance_with_findings {
        ebs_volumes {
          enable = true
        }
      }
    }
  }

  tags = {
    Environment = var.environment
    Project     = "formiq"
  }
}

# Inspector
resource "aws_inspector_assessment_target" "main" {
  name = "formiq-assessment-target"
}

resource "aws_inspector_assessment_template" "main" {
  name               = "formiq-assessment-template"
  target_arn         = aws_inspector_assessment_target.main.arn
  duration           = 3600
  rules_package_arns = [
    "arn:aws:inspector:${var.aws_region}:${data.aws_caller_identity.current.account_id}:rulespackage/0-gEjTy7T7",
    "arn:aws:inspector:${var.aws_region}:${data.aws_caller_identity.current.account_id}:rulespackage/0-rExsr2X8",
    "arn:aws:inspector:${var.aws_region}:${data.aws_caller_identity.current.account_id}:rulespackage/0-R01qwB5Q",
    "arn:aws:inspector:${var.aws_region}:${data.aws_caller_identity.current.account_id}:rulespackage/0-7WNjqgGu"
  ]

  tags = {
    Environment = var.environment
    Project     = "formiq"
  }
} 