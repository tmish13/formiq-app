#!/bin/bash

# Script to remove sensitive files from git history

echo "Removing sensitive files from git history..."

# List of patterns to remove
PATTERNS=(
    "*.env"
    ".env.*"
    "*.pem"
    "*.key"
    "*.crt"
    "*.csr"
    "*.cert"
    "secrets/*"
    "credentials/*"
    "config/secrets.yaml"
    "config/credentials.json"
)

# Create the BFG command
BFG_COMMAND="java -jar bfg.jar --delete-files "

# Add each pattern to the command
for pattern in "${PATTERNS[@]}"; do
    BFG_COMMAND+="'${pattern}' "
done

# Instructions
echo "To remove sensitive files from git history:"
echo ""
echo "1. Download BFG Repo Cleaner:"
echo "   wget https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar -O bfg.jar"
echo ""
echo "2. Create a fresh clone of your repository:"
echo "   git clone --mirror git://example.com/some-big-repo.git"
echo ""
echo "3. Run BFG to remove sensitive files:"
echo "   $BFG_COMMAND"
echo ""
echo "4. Clean up and push changes:"
echo "   cd your-repo.git"
echo "   git reflog expire --expire=now --all"
echo "   git gc --prune=now --aggressive"
echo "   git push --force"
echo ""
echo "WARNING: This will permanently remove files from git history."
echo "Make sure you have a backup before proceeding." 