#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Function to print section headers
print_header() {
    echo -e "\n${YELLOW}=== $1 ===${NC}\n"
}

# Function to generate SSL certificate
generate_cert() {
    local domain=$1
    local cert_dir="infrastructure/docker/nginx/ssl"
    local key_file="${cert_dir}/${domain}.key"
    local csr_file="${cert_dir}/${domain}.csr"
    local cert_file="${cert_dir}/${domain}.crt"
    
    print_header "Generating SSL certificate for ${domain}"
    
    # Create directory if it doesn't exist
    mkdir -p "$cert_dir"
    
    # Generate private key
    echo -e "${YELLOW}Generating private key...${NC}"
    openssl genrsa -out "$key_file" 2048
    
    # Generate CSR
    echo -e "${YELLOW}Generating CSR...${NC}"
    openssl req -new -key "$key_file" -out "$csr_file" -subj "/CN=${domain}/O=FormIQ/C=US"
    
    # Generate self-signed certificate
    echo -e "${YELLOW}Generating self-signed certificate...${NC}"
    openssl x509 -req -days 365 -in "$csr_file" -signkey "$key_file" -out "$cert_file"
    
    # Set permissions
    chmod 600 "$key_file"
    chmod 644 "$cert_file"
    
    # Clean up CSR
    rm "$csr_file"
    
    echo -e "${GREEN}SSL certificate generated for ${domain}${NC}"
    echo -e "Certificate: ${cert_file}"
    echo -e "Private key: ${key_file}"
}

# Main process
main() {
    print_header "Starting SSL Certificate Generation"
    
    # Generate certificates for domains
    generate_cert "formiq-app.com"
    generate_cert "api.formiq-app.com"
    
    print_header "SSL Certificate Generation Complete"
    echo -e "${YELLOW}Note: These are self-signed certificates for development only.${NC}"
    echo -e "${YELLOW}For production, use proper SSL certificates from a trusted CA.${NC}"
}

# Run main function
main 