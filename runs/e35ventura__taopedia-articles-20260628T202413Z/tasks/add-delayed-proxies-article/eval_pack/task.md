# Eval Task: add-delayed-proxies-article

Repository: `e35ventura/taopedia-articles` at the fixed commit in `repo_ref.txt`

## Goal
- Create a new Taopedia article at `content/pages/delayed_proxies/index.mdx`.
- The article should explain delayed proxies in Bittensor as a wallet-security concept.

## Constraints
- Edit only `content/pages/delayed_proxies/index.mdx`.
- Use this front matter exactly:

```mdx
---
title: "Delayed Proxies"
summary: "How delayed proxies add a review window before sensitive proxied actions can execute."
category: "Wallets"
tags: ["Wallets", "Security"]
---
```

- Use wiki-style internal links for related Taopedia articles.
- Include these section headings:
  - `## What the Delay Protects`
  - `## Distinction from Pure Proxies`
  - `## Distinction from Multisig Wallets`
  - `## Reader Boundary`
- Include these internal links:
  - `[[Pure Proxies]]`
  - `[[Multisig Wallets]]`
  - `[[Coldkey and Hotkey Workstation Security]]`
- Include these source links:
  - `https://docs.learnbittensor.org/keys/proxies/delayed-proxies`
  - `https://docs.learnbittensor.org/keys/proxies/proxy-types`
- Explain both of these ideas:
  - delayed proxies create a review window before execution
  - the delayed action can be canceled during that window

## Expected Outcome
- The new article exists at the required path.
- It uses the exact front matter above.
- It includes the required sections, sources, and internal links.
- No other files in the repository are changed.
