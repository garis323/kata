# PromptForge Contributor Prompt: Taopedia

Repo: `taopedia`
GitHub: `e35ventura/taopedia`

This prompt is source-grounded from repo files and the configured SN74 registry.

## Repo Overview
- Taopedia is a Bittensor-focused knowledge base for TAO, subnets, wallets, staking, mining, validation, consensus, and protocol operations. (repo:README.md)

## Contribution Rules
- Do not mix app changes with article/content changes. Do not commit generated src/content/pages output. (repo:CONTRIBUTING.md)
- Use existing CSS custom properties for colors, backgrounds, borders, and themed UI states. Do not hardcode light-only or dark-only colors unless the change is intentionally adding a new theme token. (repo:CONTRIBUTING.md)
- Contributor pull requests should target test, not main. (repo:CONTRIBUTING.md)
- Keep PRs focused. The maintainer should be able to tell what changed, why it helps Taopedia, and whether the change is worth carrying long term without having to infer the intent from the diff. (repo:CONTRIBUTING.md)
- A good PR is concrete and reviewable. It should make the Taopedia-specific benefit clear, especially when it adds code, tests, routes, dependencies, metadata, headers, workflows, or other maintenance surface. (repo:CONTRIBUTING.md)
- Small fixes and focused features are easier to review than broad cleanup. (repo:CONTRIBUTING.md)
- Call out behavior that matters for review: routes, search, metadata, build output, deployment, security, article sync, or generated data. (repo:CONTRIBUTING.md)
- If a PR creates or changes anything visible, include visual evidence in the PR description before review. (repo:CONTRIBUTING.md)

## Validation Commands
- `npm install` (repo:CONTRIBUTING.md)
- `npm run dev` (repo:CONTRIBUTING.md)

## Protected Paths
- Repository-wide ownership rules exist (`*`). (repo:.github/CODEOWNERS)

## PromptForge PR Checklist
- Run the most relevant validation commands above before opening the PR. (repo:CONTRIBUTING.md)
- Target the expected branch for your PR. (repo:CONTRIBUTING.md)
- Avoid changing protected or maintainer-owned paths unless explicitly intended. (repo:.github/CODEOWNERS)
- Include the required visual evidence for visible UI changes. (repo:CONTRIBUTING.md)

## Scoring / Registry Notes
- Registry entry found for `e35ventura/taopedia`. (https://raw.githubusercontent.com/entrius/gittensor/test/gittensor/validator/weights/master_repositories.json)
- `emission_share`: `0.05` (https://raw.githubusercontent.com/entrius/gittensor/test/gittensor/validator/weights/master_repositories.json)
- `trusted_label_pipeline`: `True` (https://raw.githubusercontent.com/entrius/gittensor/test/gittensor/validator/weights/master_repositories.json)
- `label_multipliers`: ui-ux=5.0, feature=2.0, bug=0.35, security=0.35, other=0.05 (https://raw.githubusercontent.com/entrius/gittensor/test/gittensor/validator/weights/master_repositories.json)
- `eligibility`: min_credibility=0.6, max_open_pr_threshold=4 (https://raw.githubusercontent.com/entrius/gittensor/test/gittensor/validator/weights/master_repositories.json)

## Unknowns / Caveats
- No major source gaps were detected in the current scan.

## Sources
- https://github.com/e35ventura/taopedia.git
- repo:README.md
- repo:CONTRIBUTING.md
- repo:.github/CODEOWNERS
- repo:.github/workflows/ci.yml
- repo:.github/workflows/pr-source-check.yml
- repo:.github/workflows/release.yml
- https://raw.githubusercontent.com/entrius/gittensor/test/gittensor/validator/weights/master_repositories.json
