# FAQ

## Config doesn't exist

First run: `python scripts/helper.py --json` to find vaults. Use `AskUserQuestion` to let the user pick. Write chosen path to `~/.obsidian-skill/config.json`.

## No vaults found automatically

Ask the user to type their vault path. Validate with `python scripts/validator.py --path "<path>"`. If valid, write config. If not, ask again.

## AskUserQuestion is unavailable

Fall back to plain text: "Please reply with the full path to your Obsidian vault." Wait for the user's response, then validate and save.

## Vault was moved or renamed

Run `python scripts/helper.py --json` to find current vaults. Use `AskUserQuestion` to confirm the new path. Update `~/.obsidian-skill/config.json`.

## Daily Note already has content under ## AI Sessions

Append below existing entries. Never overwrite.

## Project Note doesn't exist yet

Create from `templates/report.md`. Replace `{{project}}` with the project name and `{{date}}` with today's date.

## Same tech appears in multiple sessions

In Tech Stack Index, update the `Last seen` date and add the project if not already listed. Never duplicate entries.

## Multiple projects mentioned in one session

Create a session entry in each Project Note. In the Daily Note, list all project tags.

## User didn't specify a project name

Use "通用" as the project name. Still create the Daily Note entry — it's useful even without a project note.

## Permission denied when writing to vault

Validate vault is writable: `python scripts/validator.py --path "<vault_path>"`. Check the `checks.writable` field.

## Knowledge graph edge already exists

Skip it. Deduplicate by `(Source, Relation, Target)`.
