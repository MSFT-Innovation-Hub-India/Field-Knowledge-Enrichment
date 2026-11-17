"""Load asset JSON snapshots (batteries and stations)."""
from __future__ import annotations

import json
from pathlib import Path

from ..settings import get_settings
from .models import AssetRecord, Incident

_PROFILE_SKIP = {"incident_history", "swap_history_last_5"}


def _profile_text(data: dict) -> str:
    lines: list[str] = []
    for key, value in data.items():
        if key in _PROFILE_SKIP:
            continue
        if key == "known_issues":
            for ki in value:
                lines.append(
                    f"Known issue {ki.get('issue_code', '')}: {ki.get('issue', '')} "
                    f"(frequency: {ki.get('frequency', '')}; probable cause: {ki.get('probable_cause', '')}; "
                    f"SOP: {ki.get('linked_sop', '')})"
                )
        elif isinstance(value, (dict, list)):
            lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def parse_asset(data: dict) -> AssetRecord:
    asset_id = data["asset_id"]
    asset_type = data["asset_type"]
    incidents = []
    for inc in data.get("incident_history", []):
        incidents.append(
            Incident(
                asset_id=asset_id,
                asset_type=asset_type,
                ticket_id=inc.get("ticket_id", ""),
                date=inc.get("date_reported", ""),
                issue_code=inc.get("issue_code", ""),
                symptoms=inc.get("symptoms", ""),
                root_cause=inc.get("root_cause", ""),
                resolution=inc.get("resolution", ""),
                status=inc.get("status", "Resolved"),
                linked_sop=inc.get("linked_sop", ""),
                station_id=inc.get("station_id", ""),
            )
        )
    return AssetRecord(asset_id=asset_id, asset_type=asset_type, profile_text=_profile_text(data), incidents=incidents)


def load_assets(assets_dir: Path | None = None) -> list[AssetRecord]:
    assets_dir = assets_dir or get_settings().assets_dir
    records: list[AssetRecord] = []
    for path in sorted(assets_dir.rglob("*.json")):
        records.append(parse_asset(json.loads(path.read_text(encoding="utf-8"))))
    return records
