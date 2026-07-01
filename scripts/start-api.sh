#!/bin/bash
# Wait for NutriTrace container to be healthy
for i in $(seq 1 10); do
  if docker exec nutritrace curl -s http://localhost:3000/ > /dev/null 2>&1; then
    break
  fi
  sleep 2
done
docker exec -d nutritrace python3 /tmp/nutritrace-api.py
echo "API started"
