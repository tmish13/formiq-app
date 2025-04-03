environment = "production"
aws_region = "us-east-1"

# Availability zones
availability_zones = ["us-east-1a", "us-east-1b"]

# Subnet CIDR blocks
private_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
public_subnet_cidrs  = ["10.0.101.0/24", "10.0.102.0/24"]

# Note: Replace this with secure password management in real deployment
db_password = "${DB_PASSWORD}" 