# AGENTS.md — The Burger Lab

## Project
100% vegetarian food cart/brand in Greater Noida focused on flavorful, late-evening food, WhatsApp marketing, Google Business Profile, and local growth.

## Goals
- Create punchy WhatsApp/social content.
- Maintain Google Business Profile and digital presence assets.
- Highlight air-fried options and local Greater Noida appeal when relevant.

## Hard Rules
- The brand is strictly vegetarian. Avoid all non-veg references completely.
- Do not publish/send customer-facing messages without Rahul approval unless explicitly asked.
- Avoid generic template-like marketing.
- Keep content evergreen unless a dated campaign is requested.

## Default Workflows
- WhatsApp messages should be creative, short, pun-filled, and ready to send.
- Prefer local hooks: evening cravings, weather, weekend mood, student/office crowd.
- For cron changes: update ./cron docs and convert UTC schedules to IST in responses.
- For business facts like phone/hours/address/prices, update the canonical file first and avoid duplicate hardcoding.

## Important Paths
- Project root: /opt/data/projects/burger-lab
- Promo kit & message drafting rules: /opt/data/projects/burger-lab/promo-kit.md
- Cron docs: /opt/data/projects/burger-lab/cron
- WhatsApp script: /opt/data/projects/burger-lab/scripts/whatsapp_messages.py
- Digital presence docs: README.md and related setup docs in root

## Commands
- Inspect README.md before changing business info.
- For cron/script edits, run the script or a safe dry run where possible.
- This project may be a separate git repo/submodule; commit from inside the project root if needed.

## Model Preferences
- Default: openrouter/z-ai/glm-4.5-air:free for marketing/content; use stronger model only for complex strategy or code fixes.
- Prefer free GLM models for simple drafting, review, and planning.
- Use stronger paid/reliable models only when accuracy, coding, or complex reasoning requires it.

## Tools and Integrations
- Use file tools for reading/writing project files.
- Use terminal only for commands, tests, scripts, git, and runtime checks.
- Use web/browser only when current external information or a logged-in web session is required.

## Safety and Approval
- Do not perform destructive operations without explicit user approval.
- Do not publish, send, submit, trade, deploy, or commit unless the user explicitly asks.
- After modifying tracked files, ask whether to commit and push.

## Output Standards
- Be direct and plain-English.
- Mention files changed with absolute paths.
- State verification performed or clearly say what was not verified.
