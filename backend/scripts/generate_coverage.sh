#!/bin/bash

# Backend coverage
echo "Generating backend coverage report..."
cd backend
python -m pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

# Frontend coverage
echo "Generating frontend coverage report..."
cd ../frontend
npm run test:coverage

# Mobile coverage
echo "Generating mobile coverage report..."
cd ../mobile
npm run test:coverage

# Generate summary
echo "Coverage Summary:"
echo "----------------"
echo "Backend: $(cat backend/htmlcov/index.html | grep -o 'total.*%' | cut -d'>' -f2 | cut -d'<' -f1)"
echo "Frontend: $(cat frontend/coverage/coverage-summary.json | jq -r '.total.lines.pct')%"
echo "Mobile: $(cat mobile/coverage/coverage-summary.json | jq -r '.total.lines.pct')%" 