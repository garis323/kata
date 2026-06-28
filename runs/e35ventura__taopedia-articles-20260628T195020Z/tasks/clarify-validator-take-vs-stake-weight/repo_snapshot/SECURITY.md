# Security Policy

Taopedia Articles is a public content repository. Please report suspected vulnerabilities privately
instead of opening a public issue.

## Reporting

Email the maintainers or use GitHub private vulnerability reporting if it is enabled for this
repository.

Include:

- affected files;
- steps to reproduce;
- impact;
- suggested fix, if known.

## Contributor Safety Rules

- Do not include secrets, wallet seeds, private keys, build hook URLs, API tokens, or private
  endpoints in articles or pull requests.
- Do not add executable MDX, imports, exports, scripts, event handlers, iframes, embeds, or
  `javascript:` URLs.
- Use local image assets only when they are necessary and from trusted sources.
- Cite official or primary sources for technical claims.
- Keep article changes separate from workflow or tooling changes.

## Maintainer Rules

- Review workflow, package, and script changes with extra care.
- Treat all article content as untrusted until validation passes and a maintainer reviews it.
- Require the content validation workflow to pass before merging.

## Supported Branch

Security fixes are applied to `main`.
