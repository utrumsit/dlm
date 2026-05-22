"""
dlm config CLI — show, check, set, migrate configuration.

Usage:
    dlm config show          Print effective config with sources
    dlm config check         Validate / offer to fill missing keys
    dlm config set k v       Set a dotted-path key
    dlm config migrate       Convert legacy config.py → config.toml
"""

import importlib.util
import os
import sys
from pathlib import Path

# Use stdlib tomllib on Python 3.11+, fall back to tomli
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        print("Error: tomli is required (Python < 3.11). Install with: poetry add tomli")
        sys.exit(1)

import tomli_w

from .config_schema import Config


# ── Paths ----------------------------------------------------------------- #

XDG_CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
DLM_CONFIG_DIR = XDG_CONFIG_HOME / "dlm"

TOML_PATH = DLM_CONFIG_DIR / "config.toml"
PY_PATH = DLM_CONFIG_DIR / "config.py"

# Also check legacy library-root config.py
from .settings import LIBRARY_ROOT, LIBRARY_PY_PATH as LEGACY_LIBRARY_CONFIG


# ── Env var overrides (key → env var name) -------------------------------- #

ENV_OVERRIDES = {
    "llm.gemini.api_key": "GOOGLE_API_KEY",
}


# ── Helpers --------------------------------------------------------------- #

def _load_toml(path: Path) -> dict:
    """Load a TOML file, returning empty dict if missing."""
    if path.exists():
        with open(path, "rb") as f:
            return tomllib.load(f)
    return {}


def _save_toml(path: Path, data: dict):
    """Write a dict as TOML, creating parent dirs if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(tomli_w.dumps(data))


def _build_config(toml_data: dict) -> Config:
    """Build a Config from TOML data, applying env overrides."""
    cfg = Config.from_toml(toml_data)
    for dotted, env_name in ENV_OVERRIDES.items():
        env_val = os.environ.get(env_name, "")
        if env_val:
            Config.set_by_dotted(cfg, dotted, env_val)
    return cfg


# ── Commands -------------------------------------------------------------- #

def cmd_show(_args=None):
    """Print effective config with source annotations."""
    toml_data = _load_toml(TOML_PATH)
    cfg = _build_config(toml_data)
    keys = Config.list_keys(cfg)

    print(f"\nDLM Configuration  (config file: {TOML_PATH})\n")
    print(f"{'Key':<30} {'Value':<40} {'Source':<10}")
    print("-" * 80)

    for dotted in keys:
        value, source = Config.resolve_value(cfg, dotted, ENV_OVERRIDES.get(dotted))
        # Mask secrets
        display_val = str(value)
        if "token" in dotted or "secret" in dotted or "key" in dotted:
            if display_val and display_val != "":
                display_val = display_val[:4] + "*" * max(8, len(display_val) - 4)
            else:
                display_val = "(not set)"

        # Color-code source
        source_colors = {
            "env": "\033[94mENV\033[0m",
            "file": "\033[92mfile\033[0m",
            "default": "\033[37mdefault\033[0m",
        }
        source_str = source_colors.get(source, source)

        if len(display_val) > 38:
            display_val = display_val[:35] + "..."
        print(f"  {dotted:<28} {display_val:<40} {source_str}")

    print()


def cmd_check(_args=None):
    """Diff loaded TOML against schema, offer to write missing keys."""
    toml_data = _load_toml(TOML_PATH)
    cfg = _build_config(toml_data)
    default_cfg = Config()
    keys = Config.list_keys(cfg)

    missing = []
    for dotted in keys:
        val = Config.get_by_dotted(cfg, dotted)
        default_val = Config.get_by_dotted(default_cfg, dotted)
        if val == default_val and default_val != "":
            missing.append((dotted, default_val))

    if not missing:
        print("\n✅ All configured keys have non-default values.\n")
        return

    print(f"\n{len(missing)} key(s) at default value:\n")
    for dotted, default_val in missing:
        print(f"  [default] {dotted} = {default_val!r}")

    print()
    try:
        answer = input("Write these keys to config.toml? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if answer == "y":
        full_cfg = Config()
        full_data = full_cfg.to_dict()
        # Merge with any existing TOML data to preserve non-default overrides
        merged = {}
        for section_name, section_data in full_data.items():
            if section_name in toml_data:
                if isinstance(section_data, dict):
                    merged[section_name] = {**section_data, **toml_data[section_name]}
                    # Merge nested dicts
                    for nested_key, nested_val in section_data.items():
                        if isinstance(nested_val, dict) and nested_key in toml_data.get(section_name, {}):
                            merged[section_name][nested_key] = {
                                **nested_val, **toml_data[section_name][nested_key]
                            }
                else:
                    merged[section_name] = toml_data.get(section_name, section_data)
            else:
                merged[section_name] = section_data

        _save_toml(TOML_PATH, merged)
        print(f"  Written to {TOML_PATH}")


def cmd_set(args):
    """Set a config value by dotted path."""
    if len(args) < 2:
        print("Usage: dlm config set <dotted.path> <value>")
        print(f"\nAvailable keys:")
        for key in Config.list_keys():
            print(f"  {key}")
        sys.exit(1)

    dotted = args[0]
    value = args[1]

    if not Config.validate_key(dotted):
        print(f"Error: Unknown config key '{dotted}'.")
        print("\nDid you mean one of:")
        all_keys = Config.list_keys()
        for k in all_keys:
            if dotted.split(".")[0] == k.split(".")[0]:
                print(f"  {k}")
        sys.exit(1)

    toml_data = _load_toml(TOML_PATH)
    cfg = Config.from_toml(toml_data)

    # Try to cast value to the correct type
    default_cfg = Config()
    default_val = Config.get_by_dotted(default_cfg, dotted)
    if isinstance(default_val, int):
        try:
            value = int(value)
        except ValueError:
            print(f"Error: Expected integer for '{dotted}', got '{value}'")
            sys.exit(1)

    Config.set_by_dotted(cfg, dotted, value)

    # Rebuild TOML from config (comments will be lost — warn user)
    if TOML_PATH.exists():
        print(f"Warning: Setting '{dotted}' will overwrite config.toml (comments will be lost).")
        print("Consider editing the file directly to preserve comments.")

    new_data = cfg.to_dict()
    _save_toml(TOML_PATH, new_data)
    print(f"  Set {dotted} = {value!r}  →  {TOML_PATH}")


# ── Migration ------------------------------------------------------------- #

# Mapping from old config.py variable names to dotted config keys
_PY_TO_DOTTED = {
    "JOPLIN_TOKEN": "joplin.token",
    "JOPLIN_API_URL": "joplin.api_url",
    "JOPLIN_NOTEBOOK_NAME": "joplin.notebook_name",
    "SKIM_APP_PATH": "skim.app_path",
    "GOOGLE_API_KEY": "llm.gemini.api_key",
    "GOOGLE_CLIENT_ID": "llm.gemini.client_id",
    "GOOGLE_CLIENT_SECRET": "llm.gemini.client_secret",
}


def _load_py_config(py_path: Path):
    """Dynamically import a legacy config.py file."""
    spec = importlib.util.spec_from_file_location("user_config_legacy", py_path)
    if spec is None:
        raise ValueError(f"Cannot load config from {py_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cmd_migrate(_args=None):
    """Migrate legacy config.py → config.toml."""
    # Find the source config.py
    py_path = None
    if PY_PATH.exists():
        py_path = PY_PATH
    elif LEGACY_LIBRARY_CONFIG.exists():
        py_path = LEGACY_LIBRARY_CONFIG
    else:
        print("No config.py found. Nothing to migrate.")
        print(f"  Searched: {PY_PATH}")
        print(f"           {LEGACY_LIBRARY_CONFIG}")
        return

    # If config.toml already exists, skip (idempotent)
    if TOML_PATH.exists():
        print(f"config.toml already exists at {TOML_PATH}. Nothing to do.")
        print("  If you want to re-migrate, remove or back up the TOML file first.")
        return

    print(f"Migrating {py_path} → {TOML_PATH}\n")

    # Load the Python config
    try:
        mod = _load_py_config(py_path)
    except Exception as e:
        print(f"Error loading config.py: {e}")
        sys.exit(1)

    # Build a new config, applying migrated values
    cfg = Config()
    migrated = []
    for py_name, dotted in _PY_TO_DOTTED.items():
        if hasattr(mod, py_name):
            val = getattr(mod, py_name)
            if val:  # Only migrate non-empty values
                Config.set_by_dotted(cfg, dotted, val)
                migrated.append((dotted, val))

    if not migrated:
        print("No non-default values found in config.py. Creating empty config.toml.")
    else:
        print("Migrated values:")
        for dotted, val in migrated:
            # Mask secrets in output
            display = str(val)
            if "token" in dotted or "secret" in dotted or "key" in dotted:
                display = display[:4] + "*" * max(8, len(display) - 4) if display else "(empty)"
            print(f"  {dotted:<30} = {display}")

    # Save the TOML
    _save_toml(TOML_PATH, cfg.to_dict())
    print(f"\n  Written to {TOML_PATH}")

    # Rename old file
    bak_path = py_path.with_suffix(".py.bak")
    py_path.rename(bak_path)
    print(f"  Original backed up to {bak_path}")
    print("\n  ✅ Migration complete!")


# ── Main ------------------------------------------------------------------ #

def main():
    """Entry point for `dlm config` and `dlm-config`."""
    # Support both `dlm config <subcmd>` and `dlm-config <subcmd>`
    args = sys.argv[1:]  # strip the command name

    if not args:
        print("Usage: dlm config <subcommand> [args]")
        print()
        print("Subcommands:")
        print("  show              Show effective configuration with sources")
        print("  check             Check config against schema, offer to fill defaults")
        print("  set <key> <value> Set a config value (e.g. dlm config set readers.pdf sioyek)")
        print("  migrate           Convert legacy config.py to config.toml")
        sys.exit(0)

    subcmd = args[0]
    rest = args[1:]

    commands = {
        "show": cmd_show,
        "check": cmd_check,
        "set": cmd_set,
        "migrate": cmd_migrate,
    }

    handler = commands.get(subcmd)
    if handler is None:
        print(f"Unknown subcommand: {subcmd}")
        print("Available: " + ", ".join(commands))
        sys.exit(1)

    handler(rest)


if __name__ == "__main__":
    main()
