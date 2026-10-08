# Changelog

Published tagged releases are documented in [GitHub Releases](https://github.com/chiam-ck/nutritrace-bridge/releases). Versioned release notes and future untagged changes are recorded below.

## v2.1.3 - 2026-10-08

Fix GUI portion edits silently reverting after a successful save when diary items were created by the Singapore bridge. Repair source: [0899947](https://github.com/chiam-ck/nutritrace-bridge/commit/0899947cb9df433f5c8dd0ef9a0356314d33efba).

- The reproducible GUI overlay compares modification timestamps as instants instead of raw strings. Fresh UTC GUI edits now win over older legacy Singapore timestamps, including across midnight. Stale-edit rejection, UUID identity, independent repeated foods, concurrent additions, and tombstones are preserved.
- The root MCP handshake version is now `2.1.3`, following the existing patch-release convention.
- Bridge diary adds emit UTC `addedAt`, and diary PATCH stamps the modified item's UTC `updatedAt`. The retry guard handles timezone-aware and legacy timestamps without dropping their offsets.
- The n8n Diary Update node and generator evaluate the whole JSON request body as one expression. Numeric food ID and quantity, meal zero, and omitted optional fields are preserved; raw expression literals are no longer sent as meal values.
- Added isolated regressions: 10 merge tests, 7 bridge tests, and 5 installed n8n evaluator payload cases passed. Deployed GUI GET/PUT handlers also passed synthetic persistence, stale-edit, and tombstone checks. Interactive browser save/reload was not verified because the Mac was locked. No CI workflows or checks were configured at publication.

### Compatibility note

The legacy timezone-naive timestamp fallback is explicitly `Asia/Singapore` (`+08:00`) for this deployment. Aware timestamps retain their stated offsets. No historical diary rewrite, food-portion correction, recalculation, UUID backfill, or database migration is required by this repair. Existing diary records and intentional repeated-food entries remain unchanged. The GUI overlay is pinned to the verified NutriTrace 1.3.1 base image; see [overlay source and build instructions](overlays/nutritrace/README.md).
