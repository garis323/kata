# Eval Task: clarify-subnet-77-identity-mapping

Repository: `e35ventura/taopedia-articles` at the fixed commit in `repo_ref.txt`

## Goal
- Improve `content/pages/subnet_77/index.mdx` with a clearer, source-grounded explanation of how
  Subnet 77 maps external liquidity activity back to Bittensor rewards.

## Constraints
- Edit only `content/pages/subnet_77/index.mdx`.
- Add these section headings:
  - `## Identity Mapping Boundary`
  - `## Pool Selection Boundary`
- The new content must explain all of the following:
  - miner liquidity positions live in external liquidity pools
  - reward attribution depends on mapping an EVM address or liquidity position back to a Bittensor hotkey
  - the subnet uses a registration step to connect those identities
- Include these internal links:
  - `[[Yuma Consensus]]`
  - `[[Liquidity Positions]]`
- Include or retain these source links:
  - `https://raw.githubusercontent.com/creativebuilds/sn77/master/README.md`
  - `https://github.com/creativebuilds/sn77`
- Keep the article concise and explanatory. Do not add generic DeFi filler.

## Expected Outcome
- The article includes the required sections and concepts.
- The required internal links and source links are present.
- No files other than `content/pages/subnet_77/index.mdx` are changed.
