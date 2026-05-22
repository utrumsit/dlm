# Task: Phase 2 — Move config to TOML, add `dlm config` subcommand

## Project
DLM at ~/karl-dev/dlm. Currently config is a Python file at ~/.config/dlm/config.py loaded via importlib in src/dlm/settings.py.

## Goal
Move config to TOML (~/.config/dlm/config.toml). Add a `dlm config` subcommand for show/check/set/migrate. Keep backwards compatibility: if only config.py exists, run automatic migration on first launch.

## Read first
- src/dlm/settings.py
- src/dlm/cli.py
- config.py.example
- pyproject.toml

## Dependencies
Add to pyproject.toml under [tool.poetry.dependencies]:
- `tomli = "^2.0"` (for Python < 3.11)
- `tomli-w = "^1.0"` (TOML writer)

Use `tomllib` (stdlib) when Python >= 3.11, fall back to `tomli`.

## Create

### src/dlm/config_schema.py
A dataclass-based schema describing every key, type, default, and dotted-path:

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class JoplinConfig:
    token: str = ""
    api_url: str = "http://localhost:41184"
    notebook_name: str = "Digital Library Notes"

@dataclass
class GeminiConfig:
    api_key: str = ""
    client_id: str = ""
    client_secret: str = ""

@dataclass
class LLMConfig:
    backend: str = "gemini"      # only "gemini" supported in v1
    gemini: GeminiConfig = field(default_factory=GeminiConfig)

@dataclass
class ReadersConfig:
    pdf: str = ""                # platform default if empty
    epub: str = ""

@dataclass
class SkimConfig:
    app_path: str = "/Applications/Skim.app"

@dataclass
class SioyekConfig:
    binary: str = "sioyek"
    shared_db: str = "~/.local/share/sioyek/shared.db"

@dataclass
class FoliateConfig:
    binary: str = "foliate"
    library_dir: str = "~/.local/share/com.github.johnfactotum.Foliate/library"

@dataclass
class LibraryConfig:
    root: str = ""               # falls back to DLM_LIBRARY_ROOT env

@dataclass
class Config:
    library: LibraryConfig = field(default_factory=LibraryConfig)
    readers: ReadersConfig = field(default_factory=ReadersConfig)
    skim: SkimConfig = field(default_factory=SkimConfig)
    sioyek: SioyekConfig = field(default_factory=SioyekConfig)
    foliate: FoliateConfig = field(default_factory=FoliateConfig)
    joplin: JoplinConfig = field(default_factory=JoplinConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
```

### config.toml.example
Reflect the schema with comments explaining each section.

### src/dlm/config_cli.py
A `main()` that handles subcommands:
- `dlm config show` — print effective config; for each key show value + source (file | env | default), color-coded.
- `dlm config check` — diff loaded TOML against schema; for missing keys, print "[missing] key — default=X" and offer (y/N) to write them in.
- `dlm config set <dotted.path> <value>` — load TOML, set value, preserve comments by using tomli-w + a manual round-trip (acceptable to lose comments on `set` — print a warning).
- `dlm config migrate` — if ~/.config/dlm/config.py exists and config.toml does not: import the .py module, map known keys onto the schema, write config.toml, rename old file to config.py.bak. Print a summary of what migrated.

### Update src/dlm/settings.py
- Look for config.toml first at ~/.config/dlm/config.toml (or $XDG_CONFIG_HOME/dlm/config.toml).
- If not found and config.py exists, AUTOMATICALLY run migrate() once and proceed with the new file.
- If neither exists, proceed with all defaults plus env overrides.
- Load values into the same module-level names that already exist (JOPLIN_TOKEN, JOPLIN_API_URL, JOPLIN_NOTEBOOK_NAME, SKIM_APP_PATH, GOOGLE_API_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, LIBRARY_ROOT) so no other module needs changes yet.

## Modify
- `pyproject.toml`: add new entry point `dlm-config = "dlm.config_cli:main"`. Add tomli/tomli-w deps.

## Constraints
- Do NOT delete config.py.example yet (mark deprecated with a comment header)
- Keep cli.py callers unchanged — the same names export from settings.py
- Set must reject unknown keys against the schema
- Migration must be idempotent — running it twice is safe

## Verify
```
poetry run dlm-config show
poetry run dlm-config migrate   # if you have an old config.py
poetry run dlm-config check
poetry run dlm-config set readers.pdf sioyek
poetry run dlm --help           # everything else should still work
```
