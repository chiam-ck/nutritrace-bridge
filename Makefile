.PHONY: deploy sync api-restart mcp-restart logs food-db n8n-webhooks test clean

TECH_VM = ck@100.111.123.105
TECH_COMPOSE = docker compose -f ~/tech/docker-compose.yml
TECH_DEPLOY = /home/ck/nutritrace-deploy

# Full deploy: sync MCP files + restart containers
deploy: sync api-restart mcp-restart

# Sync MCP files to tech-vm (no restart)
sync:
	scp nutritrace-api.py $(TECH_VM):$(TECH_DEPLOY)/
	scp nutritrace-mcp.py $(TECH_VM):$(TECH_DEPLOY)/
	@echo "MCP files synced to tech-vm"

# Restart services on tech-vm
api-restart:
	ssh $(TECH_VM) '$(TECH_COMPOSE) restart nutritrace-api'

mcp-restart:
	ssh $(TECH_VM) '$(TECH_COMPOSE) restart nutritrace-mcp'

# View logs
logs:
	ssh $(TECH_VM) 'docker logs nutritrace-api --tail 50'

# Rebuild food database on tech-vm
food-db:
	scp scripts/build-sg-food-db-v2.py $(TECH_VM):$(TECH_DEPLOY)/
	ssh $(TECH_VM) 'docker cp $(TECH_DEPLOY)/build-sg-food-db-v2.py nutritrace:/tmp/ && docker exec nutritrace python3 /tmp/build-sg-food-db-v2.py'

# Create n8n MCP webhook workflows
n8n-webhooks:
	python3 scripts/create-nutritrace-n8n.py

# Quick smoke test
test:
	curl -s http://100.111.123.105:3002/health | python3 -m json.tool
	curl -s "http://100.111.123.105:3002/foods/search?q=prata&limit=2" | python3 -m json.tool

# Clean generated files
clean:
	rm -rf __pycache__ */__pycache__

# Isolated timestamp and payload regressions (no live records)
.PHONY: test-timestamps
test-timestamps:
	node --test tests/diary-merge.test.mjs
	python3 tests/test_nutritrace_timestamps.py
