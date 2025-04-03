terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# VPC and Network Configuration
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"

  name = "formiq-vpc"
  cidr = "10.0.0.0/16"

  azs             = var.availability_zones
  private_subnets = var.private_subnet_cidrs
  public_subnets  = var.public_subnet_cidrs

  enable_nat_gateway = true
  single_nat_gateway = true  # Use single NAT gateway for cost savings

  tags = {
    Environment = var.environment
    Project     = "formiq"
  }
}

# ECS Cluster - Using a simpler approach for 1,000 users
resource "aws_ecs_cluster" "main" {
  name = "formiq-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Environment = var.environment
    Project     = "formiq"
  }
}

# ECR Repositories
resource "aws_ecr_repository" "frontend" {
  name = "formiq-frontend"
  force_delete = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Environment = var.environment
    Project     = "formiq"
  }
}

resource "aws_ecr_repository" "backend" {
  name = "formiq-backend"
  force_delete = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Environment = var.environment
    Project     = "formiq"
  }
}

# RDS Instance - t3.small for 1,000 users
resource "aws_db_instance" "main" {
  identifier           = "formiq-db"
  engine              = "postgres"
  engine_version      = "15"
  instance_class      = "db.t3.small"  # Optimized for 1,000 users
  allocated_storage   = 20
  storage_type        = "gp2"
  
  db_name             = "formiq"
  username           = "postgres"
  password           = var.db_password
  
  backup_retention_period = 7  # Keep 7 days of backups
  skip_final_snapshot = false
  final_snapshot_identifier = "formiq-db-final-snapshot"
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  parameter_group_name = aws_db_parameter_group.main.name

  tags = {
    Environment = var.environment
    Project     = "formiq"
  }
}

# Create DB subnet group
resource "aws_db_subnet_group" "main" {
  name       = "formiq-db-subnet-group"
  subnet_ids = module.vpc.private_subnets

  tags = {
    Environment = var.environment
    Project     = "formiq"
  }
}

# RDS Parameter group for connection pooling
resource "aws_db_parameter_group" "main" {
  name   = "formiq-db-params"
  family = "postgres15"

  parameter {
    name  = "max_connections"
    value = "100"  # Sufficient for 1,000 users
  }

  tags = {
    Environment = var.environment
    Project     = "formiq"
  }
}

# ElastiCache Redis - Small instance for caching
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "formiq-redis"
  engine              = "redis"
  node_type           = "cache.t3.micro"  # Sufficient for MVP
  num_cache_nodes     = 1
  parameter_group_name = "default.redis7"
  port                = 6379

  security_group_ids = [aws_security_group.redis.id]
  subnet_group_name  = aws_elasticache_subnet_group.main.name

  tags = {
    Environment = var.environment
    Project     = "formiq"
  }
}

# Create ElastiCache subnet group
resource "aws_elasticache_subnet_group" "main" {
  name       = "formiq-cache-subnet-group"
  subnet_ids = module.vpc.private_subnets

  tags = {
    Environment = var.environment
    Project     = "formiq"
  }
}

# Security Groups
resource "aws_security_group" "rds" {
  name        = "formiq-rds-sg"
  description = "Security group for RDS"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }
}

resource "aws_security_group" "redis" {
  name        = "formiq-redis-sg"
  description = "Security group for Redis"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }
}

resource "aws_security_group" "ecs_tasks" {
  name        = "formiq-ecs-tasks-sg"
  description = "Security group for ECS tasks"
  vpc_id      = module.vpc.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Setup S3 bucket for video storage
resource "aws_s3_bucket" "video_storage" {
  bucket = "formiq-video-storage"

  tags = {
    Environment = var.environment
    Project     = "formiq"
  }
}

# S3 bucket for static website assets
resource "aws_s3_bucket" "frontend_assets" {
  bucket = "formiq-frontend-assets"

  tags = {
    Environment = var.environment
    Project     = "formiq"
  }
}

# Make the static assets bucket public
resource "aws_s3_bucket_public_access_block" "frontend_assets" {
  bucket = aws_s3_bucket.frontend_assets.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# EC2 instance for backend (simplified approach for MVP)
resource "aws_instance" "backend" {
  ami           = "ami-0c55b159cbfafe1f0" # Amazon Linux 2
  instance_type = "t3.medium"  # Good balance for 1,000 users
  subnet_id     = module.vpc.public_subnets[0]
  
  vpc_security_group_ids = [aws_security_group.backend.id]
  
  tags = {
    Name        = "formiq-backend"
    Environment = var.environment
    Project     = "formiq"
  }
}

# Security group for backend instance
resource "aws_security_group" "backend" {
  name        = "formiq-backend-sg"
  description = "Security group for backend EC2 instance"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # In production, limit to specific IPs
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Load Balancer
resource "aws_lb" "main" {
  name               = "formiq-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]

  subnets = module.vpc.public_subnets

  tags = {
    Environment = var.environment
    Project     = "formiq"
  }
}

resource "aws_security_group" "alb" {
  name        = "formiq-alb-sg"
  description = "Security group for ALB"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
} 