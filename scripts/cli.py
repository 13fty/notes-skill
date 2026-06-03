#!/usr/bin/env python3
"""obsidian-skill — Unified CLI for managing Obsidian vault integration.

Usage:
    obsidian-skill <command> [options]

Commands:
    init       First-time setup wizard
    config     View or modify configuration
    validate   Check vault health
    search     Find Obsidian vaults on this system
    repair     Recover a broken vault path
    sync       Write AI output blocks to vault
    migrate    Upgrade config version
    doctor     Full system diagnostic
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure lib/ is importable when running from project root
_script_dir = Path(__file__).resolve().parent
_project_root = _script_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from lib.config import (
    load_config, save_config, config_exists, get_vault_path, set_vault_path,
    export_config, config_get, config_set, get_preference, set_preference,
    record_sync, record_discovered_vault, get_discovered_vaults,
    run_migrations, doctor_check as config_doctor,
    DEFAULT_CONFIG,
)
from lib.vault import (
    search_vaults, search_vaults_simple, validate_vault,
    repair_vault, format_validation_report, doctor_check as vault_doctor,
)
from lib.sync import sync_to_vault
from lib.templates import list_templates, render_template


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _fail(msg: str, code: int = 1):
    print(f"[error] {msg}", file=sys.stderr)
    sys.exit(code)


# ── Command handlers ────────────────────────────────────────────────────────────

def cmd_init(args: argparse.Namespace) -> int:
    """First-time initialization wizard."""
    if config_exists() and not args.force:
        vault = get_vault_path()
        print(f"Config already exists. Vault: {vault}")
        print("Use --force to re-initialize.")
        return 0

    vault_path = args.vault
    if vault_path:
        # Direct path provided
        result = validate_vault(vault_path)
        if not result["valid"]:
            print(format_validation_report(result))
            _fail("Provided vault path is not valid. Check the report above.")
        set_vault_path(vault_path)
        record_discovered_vault(vault_path, result["name"], valid=True)
        print(f"✅ Vault configured: {vault_path}")
        return 0

    # Interactive flow: search first
    vaults = search_vaults()
    valid_vaults = [v for v in vaults if v["valid"]]

    if valid_vaults:
        print(f"Found {len(valid_vaults)} Obsidian vault(s):\n")
        for i, v in enumerate(valid_vaults):
            name = v["name"]
            path = v["path"]
            warnings = f" ({len(v['warnings'])} warnings)" if v["warnings"] else ""
            print(f"  [{i + 1}] {name} — {path}{warnings}")

        if args.noninteractive:
            chosen = valid_vaults[0]
        else:
            print()
            try:
                choice = input(f"Select vault [1-{len(valid_vaults)}] or press Enter for first: ").strip()
                idx = int(choice) - 1 if choice else 0
                if idx < 0 or idx >= len(valid_vaults):
                    _fail(f"Invalid selection: {choice}")
                chosen = valid_vaults[idx]
            except (EOFError, KeyboardInterrupt):
                print("\nAborted.")
                return 1

        set_vault_path(chosen["path"])
        record_discovered_vault(chosen["path"], chosen["name"], valid=True)
        print(f"✅ Vault configured: {chosen['path']}")
        return 0

    # No vaults found — ask for path
    if args.noninteractive:
        _fail("No vaults found and --noninteractive set. Use --vault to specify path.")

    print("No Obsidian vaults found automatically.")
    try:
        path = input("Enter your vault path: ").strip()
        if not path:
            _fail("No path provided.")
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        return 1

    result = validate_vault(path)
    if not result["valid"]:
        print(format_validation_report(result))
        _fail("Provided path is not a valid Obsidian vault.")

    set_vault_path(path)
    record_discovered_vault(path, result["name"], valid=True)
    print(f"✅ Vault configured: {path}")
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    """View or modify configuration."""
    if args.action == "list":
        print(export_config())
    elif args.action == "get":
        if not args.key:
            _fail("config get requires a key, e.g. 'vault_path' or 'preferences.language'")
        value = config_get(args.key)
        if value is None:
            _fail(f"Key not found: {args.key}")
        if isinstance(value, (dict, list)):
            _print_json(value)
        else:
            print(value)
    elif args.action == "set":
        if not args.key or args.value is None:
            _fail("config set requires <key> <value>, e.g. 'preferences.language en'")
        # Try to parse JSON values (bool, int, list, dict)
        try:
            parsed_value = json.loads(args.value)
        except (json.JSONDecodeError, ValueError):
            parsed_value = args.value
        config_set(args.key, parsed_value)
        print(f"✅ Set {args.key} = {json.dumps(parsed_value, ensure_ascii=False)}")
    elif args.action == "reset":
        save_config(dict(DEFAULT_CONFIG))
        print("✅ Config reset to defaults.")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate the configured or specified vault."""
    path = args.path or get_vault_path()
    if not path:
        _fail("No vault configured. Run 'obsidian-skill init' first, or pass --path.")

    result = validate_vault(path)
    if args.json:
        _print_json(result)
    else:
        print(format_validation_report(result))

    return 0 if result["valid"] else 1


def cmd_search(args: argparse.Namespace) -> int:
    """Search for Obsidian vaults on this system."""
    vaults = search_vaults()
    if not vaults:
        print("No vaults found.")
        return 0

    if args.json:
        _print_json(vaults)
    else:
        for v in vaults:
            icon = "✅" if v["valid"] else "❌"
            print(f"{icon} {v['name']:20s}  {v['path']}")
            for w in v.get("warnings", []):
                print(f"   ⚠️  {w}")
        print(f"\n{len(vaults)} vault(s) found.")

    # Update discovered_vaults in state
    for v in vaults:
        record_discovered_vault(v["path"], v["name"], valid=v["valid"])

    return 0


def cmd_repair(args: argparse.Namespace) -> int:
    """Repair a broken vault configuration."""
    vault_path = get_vault_path()
    if not vault_path:
        _fail("No vault configured. Run 'obsidian-skill init' first.")

    discovered = get_discovered_vaults()
    result = repair_vault(vault_path, discovered)

    print(result["message"])
    if result["candidates"]:
        print("\nCandidates:")
        for i, c in enumerate(result["candidates"]):
            mark = " ← best match" if c == result.get("new_path") else ""
            print(f"  [{i + 1}] {c}{mark}")

        if result["repaired"] and not args.dry_run:
            try:
                choice = input(f"\nAccept '{result['new_path']}'? [Y/n]: ").strip().lower()
                if choice in ("", "y", "yes"):
                    set_vault_path(result["new_path"])
                    print(f"✅ Updated vault path: {result['new_path']}")
                    return 0
            except (EOFError, KeyboardInterrupt):
                print("\nAborted.")
                return 1

            print("No changes made. Run 'obsidian-skill init --force' to reconfigure.")
    else:
        print("No candidates found. Run 'obsidian-skill init --force' to reconfigure.")

    return 1 if not result["repaired"] else 0


def cmd_sync(args: argparse.Namespace) -> int:
    """Sync AI output blocks to the vault."""
    vault_path = get_vault_path()
    if not vault_path:
        _fail("No vault configured. Run 'obsidian-skill init' first.")

    if args.input:
        text = Path(args.input).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    results = sync_to_vault(vault_path, text, dry_run=args.dry_run)

    files_written = 0
    files_updated = 0
    for r in results:
        status = r["status"]
        if args.verbose or args.dry_run:
            print(f"[{status}] {r['action']} → {r['path']}")

        if status in ("created", "created-with-section"):
            files_written += 1
        elif status in ("appended-to-section", "appended-end", "appended-new-section", "section-replaced"):
            files_updated += 1

    if not args.dry_run and results:
        record_sync(
            session_id=args.session_id or "cli",
            project=args.project or "unknown",
            files_written=files_written,
            files_updated=files_updated,
        )

    print(f"\nDone: {files_written} written, {files_updated} updated, {len(results)} total blocks.")
    return 0


def cmd_migrate(args: argparse.Namespace) -> int:
    """Run pending config migrations."""
    before = load_config().get("version", "unknown")
    cfg = run_migrations()
    after = cfg.get("version", "unknown")
    if before != after:
        print(f"✅ Migrated config from {before} → {after}")
    else:
        print(f"✅ Config is up to date (version {after})")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    """Run a full diagnostic and print a report."""
    report = {
        "config": config_doctor(),
        "vault": vault_doctor(),
        "templates": list_templates(),
    }

    if args.json:
        _print_json(report)
        return 0

    # Human-readable report
    print("=== obsidian-skill doctor ===\n")

    print("📁 Config:")
    c = report["config"]
    print(f"  Config dir:  {'✅' if c['config_dir_exists'] else '❌'} ~/.obsidian-skill/")
    print(f"  Config file: {'✅' if c['config_file_exists'] else '❌'} config.json")
    print(f"  State file:  {'✅' if c['state_file_exists'] else '❌'} state.json")
    print(f"  Vault path:  {'✅' if c['vault_configured'] else '❌'}")

    print("\n🔍 Vault:")
    v = report["vault"]
    if v["validation"]:
        vr = v["validation"]
        print(f"  Status: {'✅ Valid' if vr['valid'] else '❌ Invalid'}")
        print(f"  Path:   {vr['path']}")
        for w in vr.get("warnings", []):
            print(f"  ⚠️  {w}")
    elif v["vault_configured"]:
        print("  ⚠️  No vault configured")
    else:
        print("  ⚠️  Not configured — run 'obsidian-skill init'")

    if v.get("all_vaults_found"):
        print(f"\n📋 Discovered vaults ({len(v['all_vaults_found'])}):")
        for dv in v["all_vaults_found"]:
            print(f"  - {dv}")

    print(f"\n📝 Templates ({len(report['templates'])}):")
    for t in report["templates"]:
        print(f"  - {t}.md")

    all_good = c["vault_configured"] and (v.get("validation") and v["validation"]["valid"])
    print(f"\n{'✅ All checks pass' if all_good else '⚠️  Some checks need attention'}")
    return 0 if all_good else 1


# ── CLI Definition ──────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="obsidian-skill",
        description="Manage Obsidian vault integration for AI agent sessions.",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # init
    p_init = sub.add_parser("init", help="First-time setup wizard")
    p_init.add_argument("--vault", help="Directly specify vault path (skip search)")
    p_init.add_argument("--force", action="store_true", help="Re-initialize even if config exists")
    p_init.add_argument("--noninteractive", action="store_true", help="Run without user prompts")

    # config
    p_config = sub.add_parser("config", help="View or modify configuration")
    p_config.add_argument("action", choices=["list", "get", "set", "reset"],
                          help="list=get all, get=<key>, set=<key> <value>, reset=defaults")
    p_config.add_argument("key", nargs="?", help="Config key (dotted, e.g. 'preferences.language')")
    p_config.add_argument("value", nargs="?", help="Value to set")

    # validate
    p_val = sub.add_parser("validate", help="Check vault health")
    p_val.add_argument("--path", help="Vault path (default: from config)")
    p_val.add_argument("--json", action="store_true", help="Output as JSON")

    # search
    p_search = sub.add_parser("search", help="Find Obsidian vaults on this system")
    p_search.add_argument("--json", action="store_true", help="Output as JSON")

    # repair
    p_repair = sub.add_parser("repair", help="Recover a broken vault path")
    p_repair.add_argument("--dry-run", action="store_true", help="Show candidates without applying")

    # sync
    p_sync = sub.add_parser("sync", help="Write AI output blocks to vault")
    p_sync.add_argument("--input", help="Input file (default: stdin)")
    p_sync.add_argument("--dry-run", action="store_true", help="Simulate without writing")
    p_sync.add_argument("--verbose", "-v", action="store_true", help="Show per-file status")
    p_sync.add_argument("--session-id", help="Session identifier for state tracking")
    p_sync.add_argument("--project", help="Project name for state tracking")

    # migrate
    sub.add_parser("migrate", help="Upgrade config version")

    # doctor
    p_doctor = sub.add_parser("doctor", help="Full system diagnostic")
    p_doctor.add_argument("--json", action="store_true", help="Output as JSON")

    return parser


# ── Entry point ────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    handlers = {
        "init": cmd_init,
        "config": cmd_config,
        "validate": cmd_validate,
        "search": cmd_search,
        "repair": cmd_repair,
        "sync": cmd_sync,
        "migrate": cmd_migrate,
        "doctor": cmd_doctor,
    }

    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
