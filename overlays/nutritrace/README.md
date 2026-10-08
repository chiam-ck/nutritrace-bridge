# NutriTrace GUI timestamp overlay

This is the canonical source for the local GUI timestamp repair deployed alongside NutriBridge. The base GUI is NutriTrace 1.3.1 from [TraceApps/nutritrace](https://github.com/TraceApps/nutritrace), revision `a49eb1df9494d3c05604819cca5c7c8fb67aadeb`. The Dockerfile pins the deployed base image digest and replaces only `/app/lib/diary-merge.js`.

The merge compares timestamp instants rather than raw ISO strings. A legacy timezone-naive item timestamp from this deployment's Singapore bridge is interpreted as `+08:00`; aware timestamps retain their stated offset. Missing or invalid values rank below valid timestamps. Incoming entries still win millisecond ties; UUID identity, ordering, stale-edit rejection, concurrent preservation, and tombstones retain their existing behavior. This Singapore fallback is specific to this deployment, not a universal upstream timezone rule.

Build from the repository root:

```sh
docker build --pull=false --network=none -f overlays/nutritrace/Dockerfile -t nutritrace-local:timestamp-fix-20261009 overlays/nutritrace
```

Building does not deploy or restart a service. Keep the existing compose ports, environment, volumes and networks; only select the resulting image for the GUI service through the normal reviewed deployment process. No database migration or nutrition-record rewrite is required.

The overlay module derives from the upstream `server/lib/diary-merge.js` and is covered by the upstream AGPL-3.0 license reproduced in [LICENSE](LICENSE). The timestamp normalization modifications are maintained in this repository; the base project attribution remains with TraceApps and its contributors.

Run the repair's isolated regressions from the repository root:

```sh
node --test tests/diary-merge.test.mjs
python3 tests/test_nutritrace_timestamps.py
python3 tests/emit-n8n-expression-test.py | docker exec -i homelab-n8n node
```

These tests use pure merge functions, temporary synthetic SQLite databases, and the installed n8n expression evaluator with synthetic payloads. They never access a real diary or execute a workflow. The n8n command assumes the existing local `homelab-n8n` container. The bridge tests load the canonical root `nutritrace-api.py`; the historical supplementary `src/` adapters are not deployed by this repair.
