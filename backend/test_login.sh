!/bin/bash

BASE="https://formiq-api.onrender.com"

EMAIL="tarpanboss@gmail.com"
PASSWORD="mishra2004!"

echo "---- LOGIN ----"

RESPONSE=$(curl -s -X POST "$BASE/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$EMAIL&password=$PASSWORD")

echo "$RESPONSE" | python3 -m json.tool

TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; 
d=json.load(sys.stdin); print(d.get('access_token','FAILED'))")

echo ""
echo "TOKEN:"
echo "$TOKEN"

echo ""
echo "---- USERS ME ----"

curl -s -X GET "$BASE/api/v1/users/me" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool

