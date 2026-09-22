# Project Architecture

## Overview
Replace this file with your real architecture docs, READMEs, ADRs, config files, and
exported PR descriptions that capture the "why" behind design decisions.

## Example: Why Postgres over MongoDB
We chose Postgres because our data is relational and we needed ACID transactions for
billing events. MongoDB was evaluated in Q3 2023 but rejected due to join complexity.

## Example: Auth Flow
Authentication is handled in `src/auth/middleware.py`. We use JWT tokens with a 1-hour
expiry. Refresh tokens are stored in Redis (not Postgres) to allow fast revocation.

## How to populate this folder
Drop in any of the following:
- README.md files from your repos
- Architecture Decision Records (ADRs)
- Design documents
- Exported merged-PR descriptions
- Key config files with inline comments explaining settings
