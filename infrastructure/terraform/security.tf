# WAF Web ACL
resource "aws_wafv2_web_acl" "main" {
  name        = "formiq-web-acl"
  description = "WAF Web ACL for FormIQ"
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  # Rate limiting rule
  rule {
    name     = "RateLimitRule"
    priority = 1

    override_action {
      none {}
    }

    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "RateLimitRuleMetric"
      sampled_requests_enabled  = true
    }
  }

  # SQL injection rule
  rule {
    name     = "SQLiRule"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "SQLiRuleMetric"
      sampled_requests_enabled  = true
    }
  }

  # XSS rule
  rule {
    name     = "XSSRule"
    priority = 3

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
      metric_name               = "XSSRuleMetric"
      sampled_requests_enabled  = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name               = "FormIQWebACLMetric"
    sampled_requests_enabled  = true
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