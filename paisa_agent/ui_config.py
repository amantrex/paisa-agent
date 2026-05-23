import json
import os
from dataclasses import asdict
from pathlib import Path
from .config import Settings

# Path to UI settings JSON (stored in project root)
UI_SETTINGS_PATH = Path(__file__).parent / "ui_settings.json"

def load_ui_settings() -> dict:
    """Load UI settings from JSON file. If not present, return defaults from Settings."""
    if UI_SETTINGS_PATH.is_file():
        try:
            with open(UI_SETTINGS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            # fall back to defaults on error
            pass
    # Return defaults from Settings dataclass
    defaults = asdict(Settings())
    # Keep only guard‑rail related keys
    keys = [
        "commission_per_share",
        "slippage_pct",
        "max_daily_loss_pct",
        "max_position_pct",
        "portfolio_opt_top_n",
        "stop_loss_pct",
        "take_profit_pct",
    ]
    return {k: defaults[k] for k in keys if k in defaults}

def save_ui_settings(settings_dict: dict) -> None:
    """Persist UI settings to JSON file. Only writes allowed guard‑rail keys."""
    # Ensure directory exists
    UI_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Filter to known keys
    allowed_keys = {
        "commission_per_share",
        "slippage_pct",
        "max_daily_loss_pct",
        "max_position_pct",
        "portfolio_opt_top_n",
        "stop_loss_pct",
        "take_profit_pct",
    }
    filtered = {k: v for k, v in settings_dict.items() if k in allowed_keys}
    with open(UI_SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(filtered, f, indent=2)
