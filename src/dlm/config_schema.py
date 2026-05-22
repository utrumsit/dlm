"""
DLM Configuration Schema

Dataclass-based schema describing every config key, its type, default,
and dotted-path notation. Used by the TOML loader, CLI, and migration.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
import os


@dataclass
class JoplinConfig:
    """Joplin Web Clipper settings."""
    token: str = ""
    api_url: str = "http://localhost:41184"
    notebook_name: str = "Digital Library Notes"

    _dotted_prefix = "joplin"


@dataclass
class GeminiConfig:
    """Google Gemini API / OAuth settings."""
    api_key: str = ""
    client_id: str = ""
    client_secret: str = ""

    _dotted_prefix = "llm.gemini"


@dataclass
class LLMConfig:
    """LLM backend settings."""
    backend: str = "gemini"      # only "gemini" supported in v1
    gemini: GeminiConfig = field(default_factory=GeminiConfig)

    _dotted_prefix = "llm"


@dataclass
class ReadersConfig:
    """Reader application overrides (empty = platform default)."""
    pdf: str = ""
    epub: str = ""

    _dotted_prefix = "readers"


@dataclass
class SkimConfig:
    """Skim.app (macOS PDF reader) settings."""
    app_path: str = "/Applications/Skim.app"

    _dotted_prefix = "skim"


@dataclass
class SioyekConfig:
    """Sioyek (Linux/macOS PDF reader) settings."""
    binary: str = "sioyek"
    shared_db: str = "~/.local/share/sioyek/shared.db"

    _dotted_prefix = "sioyek"


@dataclass
class FoliateConfig:
    """Foliate (Linux EPUB reader) settings."""
    binary: str = "foliate"
    # Parent dir containing library/uri-store.json and <identifier>.json files
    library_dir: str = "~/.local/share/com.github.johnfactotum.Foliate"

    _dotted_prefix = "foliate"


@dataclass
class LibraryConfig:
    """Library root settings (falls back to DLM_LIBRARY_ROOT env var)."""
    root: str = ""

    _dotted_prefix = "library"


@dataclass
class Config:
    """Root configuration object."""
    library: LibraryConfig = field(default_factory=LibraryConfig)
    readers: ReadersConfig = field(default_factory=ReadersConfig)
    skim: SkimConfig = field(default_factory=SkimConfig)
    sioyek: SioyekConfig = field(default_factory=SioyekConfig)
    foliate: FoliateConfig = field(default_factory=FoliateConfig)
    joplin: JoplinConfig = field(default_factory=JoplinConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)

    # ---- Helpers --------------------------------------------------------- #

    @classmethod
    def from_toml(cls, data: dict) -> "Config":
        """Build a Config from a dict (typically parsed from a TOML file)."""
        from dataclasses import MISSING
        # Navigate nested dicts into matching dataclasses
        def _build(config_cls, raw: dict):
            kwargs = {}
            for fname, ftype in config_cls.__dataclass_fields__.items():
                if fname.startswith("_"):
                    continue
                if fname in raw:
                    if ftype.default_factory is not MISSING:
                        # Nested dataclass — default_factory IS the constructor
                        nested_cls = ftype.default_factory
                        kwargs[fname] = _build(nested_cls, raw[fname])
                    else:
                        kwargs[fname] = raw[fname]
            return config_cls(**kwargs)

        return _build(cls, data)

    def to_dict(self) -> dict:
        """Flatten config to a plain dict (for TOML serialisation)."""
        return asdict(self)

    @staticmethod
    def list_keys(cfg=None):
        """Return a list of dotted-path keys in schema order."""
        from dataclasses import MISSING
        if cfg is None:
            cfg = Config()
        keys = []
        # Flat fields
        sections = [
            ("library", cfg.library, LibraryConfig),
            ("readers", cfg.readers, ReadersConfig),
            ("skim", cfg.skim, SkimConfig),
            ("sioyek", cfg.sioyek, SioyekConfig),
            ("foliate", cfg.foliate, FoliateConfig),
            ("joplin", cfg.joplin, JoplinConfig),
            ("llm", cfg.llm, LLMConfig),
        ]
        for prefix, sub, sub_cls in sections:
            for fname, ftype in sub_cls.__dataclass_fields__.items():
                if fname.startswith("_"):
                    continue
                if ftype.default_factory is not MISSING:
                    # Nested dataclass (e.g. llm -> gemini)
                    nested = ftype.default_factory()
                    for nfname, nftype in nested.__class__.__dataclass_fields__.items():
                        if nfname.startswith("_"):
                            continue
                        keys.append(f"{prefix}.{fname}.{nfname}")
                else:
                    keys.append(f"{prefix}.{fname}")
        return keys

    @staticmethod
    def get_by_dotted(cfg, dotted: str):
        """Get a value by dotted path (e.g. 'joplin.token')."""
        parts = dotted.split(".")
        obj = cfg
        for part in parts:
            obj = getattr(obj, part, None)
            if obj is None:
                raise KeyError(f"Unknown config key: {dotted}")
        return obj

    @staticmethod
    def set_by_dotted(cfg, dotted: str, value):
        """Set a value by dotted path, validating against schema."""
        parts = dotted.split(".")
        obj = cfg
        for part in parts[:-1]:
            obj = getattr(obj, part, None)
            if obj is None:
                raise KeyError(f"Unknown config key: {dotted}")
        attr = parts[-1]
        if not hasattr(obj, attr):
            raise KeyError(f"Unknown config key: {dotted}")
        setattr(obj, attr, value)

    @staticmethod
    def validate_key(dotted: str) -> bool:
        """Check if a dotted-path key exists in the schema."""
        try:
            cfg = Config()
            Config.get_by_dotted(cfg, dotted)
            return True
        except KeyError:
            return False

    # ---- Source tracking ------------------------------------------------- #

    @staticmethod
    def resolve_value(cfg, dotted: str, env_name: Optional[str] = None) -> tuple:
        """
        Resolve the effective value and its source for a dotted key.
        Returns (value, source) where source is 'env' | 'file' | 'default'.
        """
        raw = Config.get_by_dotted(cfg, dotted)
        # Check env override first
        if env_name and os.environ.get(env_name):
            return (os.environ[env_name], "env")
        # Default instance for comparison
        default_cfg = Config()
        default_val = Config.get_by_dotted(default_cfg, dotted)
        if raw != default_val:
            return (raw, "file")
        return (default_val, "default")
