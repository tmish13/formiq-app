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
  single_nat_gateway = var.environment == "production" ? false : true

  tags = {
    Environment = var.environment
    Project     = "formiq"
  }
}

# ECS Cluster
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

# RDS Instance
resource "aws_db_instance" "main" {
  identifier           = "formiq-db"
  engine              = "postgres"
  engine_version      = "15"
  instance_class      = var.environment == "production" ? "db.t3.micro" : "db.t3.micro"
  allocated_storage   = 20
  storage_type        = "gp2"
  
  db_name             = "formiq"
  username           = "postgres"
  password           = var.db_password
  
  skip_final_snapshot = var.environment != "production"
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  tags = {
    Environment = var.environment
    Project     = "formiq"
  }
}

# ElastiCache Redis
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "formiq-redis"
  engine              = "redis"
  node_type           = var.environment == "production" ? "cache.t3.micro" : "cache.t3.micro"
  num_cache_nodes     = 1
  parameter_group_family = "redis7"
  port                = 6379

  security_group_ids = [aws_security_group.redis.id]
  subnet_group_name  = aws_elasticache_subnet_group.main.name

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