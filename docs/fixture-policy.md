# Fixture policy

Fixtures are public, deterministic test inputs—not an archive of scraped content.

Each fixture must:

1. use fixed UTC timestamps, stable identifiers, and deterministic ordering;
2. contain no secrets, cookies, personal data, or private endpoints;
3. retain source URLs and only the minimum source excerpt required to test a
   parser or explain evidence;
4. identify whether it is synthetic, sanitized, or redistribution-approved;
5. cover its intended state, such as normal, missing, malformed, blocked, stale,
   corrected, rate-limited, or conflicting;
6. be validated by CI through the public contract model.

Never refresh fixtures automatically from a live source in CI. Live smoke tests
must be manual, use tiny allowlists, and obey source access rules.

