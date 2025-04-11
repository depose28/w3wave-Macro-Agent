#!/bin/bash

# Build the Docker image
docker build -t macro-agent supabase/functions/macro-agent/

# Create a container from the image
docker create --name macro-agent-container macro-agent

# Copy the function files to a temporary directory
mkdir -p .temp/macro-agent
docker cp macro-agent-container:/app/. .temp/macro-agent/

# Clean up
docker rm macro-agent-container

# Deploy to Supabase
curl -X POST "https://api.supabase.com/v1/projects/syaeekyjwrfaqunyhwjf/functions" \
  -H "Authorization: Bearer $DB_SERVICE_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "macro-agent",
    "verify_jwt": false
  }'

# Upload the function files
cd .temp/macro-agent
zip -r ../macro-agent.zip .
cd ../..

curl -X PUT "https://api.supabase.com/v1/projects/syaeekyjwrfaqunyhwjf/functions/macro-agent" \
  -H "Authorization: Bearer $DB_SERVICE_KEY" \
  -H "Content-Type: application/zip" \
  --data-binary @.temp/macro-agent.zip

# Clean up
rm -rf .temp 