# Docker conventions for contract consumers

Collectors are independently runnable services but share these conventions:

- implement `GET /health`, `GET /v1/capabilities`, and `POST /v1/collect`;
- expose a matching CLI and a deterministic fixture mode;
- run as a non-root user with a read-only root filesystem where practical;
- use an internal Compose network; collector ports are not published to the host;
- accept the pinned contract package version at image build time;
- publish immutable semantic-version and digest-pinned images;
- keep operational HTTP caches on a separate volume from optional user data;
- receive credentials through `.env.local` or local Docker secrets, never image
  layers, Compose defaults, command-line arguments, or contract payloads;
- include health checks, bounded timeouts, cancellation, and graceful shutdown;
- return partial failures rather than discarding successful evidence.

The workbench may publish its own port to localhost. It should call collectors by
Compose service name, pin released image digests, and remain usable when an
optional provider is disabled or unavailable.

