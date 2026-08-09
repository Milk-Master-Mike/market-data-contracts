# Security Policy

## Supported versions

Security fixes are provided for the latest minor release of the current major
version. Consumers should pin a release and enable automated dependency updates.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability or leaked credential.
Use GitHub's private vulnerability reporting for this repository. Include the
affected version, impact, minimal reproduction, and any proposed mitigation.

## Secrets and sensitive data

- Never place API keys, cookies, tokens, passwords, or private endpoints in a
  request, response, fixture, log, export, or issue.
- Use an ignored `.env.local` file or a local Docker secret at runtime.
- The contract intentionally rejects secret-like `source_settings` keys, but this
  is defense in depth rather than a credential vault.
- Sanitize recorded HTTP responses and retain only content allowed by the source.

Normalized external content remains untrusted. Consumers must escape it in user
interfaces and must not let it become executable instructions for an assistant,
shell, browser, or trading system.

