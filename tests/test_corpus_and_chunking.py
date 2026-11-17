import re

from knowledge_enrichment.corpus import load_assets, load_installed_sops, load_mapping, parse_sop_text
from knowledge_enrichment.kb import chunking
from knowledge_enrichment.settings import get_settings

KEY_OK = re.compile(r"^[A-Za-z0-9_\-=]+$")


def _sops():
    s = get_settings()
    return load_installed_sops(s.sops_dir, load_mapping(s.config_dir))


def test_installed_sops_parse_issue_type_codes_and_applicability():
    sops = {s.sop_id: s for s in _sops()}
    assert set(sops) == {"SOP-BAT-001", "SOP-BAT-002", "SOP-BAT-003", "SOP-GEN-001", "SOP-STN-001", "SOP-STN-002", "SOP-STN-003"}
    assert sops["SOP-BAT-001"].issue_type == "Battery Over Temperature Thermal Event"
    assert {"W-310", "E-604"} <= set(sops["SOP-BAT-001"].error_codes)
    assert sops["SOP-BAT-001"].applies_to == ["battery", "station"]   # override
    assert sops["SOP-BAT-003"].applies_to == ["battery"]
    assert sops["SOP-STN-003"].applies_to == ["station"]
    assert sops["SOP-GEN-001"].applies_to == ["station"]
    assert len(sops["SOP-BAT-001"].sections) == 6


def test_chunk_ids_are_valid_search_keys_and_unique():
    s = get_settings()
    chunks = []
    for sop in _sops():
        chunks += chunking.sop_section_chunks(sop)
        chunks.append(chunking.sop_catalog_chunk(sop, "summary"))
    for asset in load_assets(s.assets_dir):
        chunks.append(chunking.asset_profile_chunk(asset))
        chunks += [chunking.incident_chunk(i) for i in asset.incidents]
    ids = [c["id"] for c in chunks]
    assert len(ids) == len(set(ids)) == 73
    assert all(KEY_OK.match(i) for i in ids)


def test_chunk_header_states_asset_type():
    sops = {s.sop_id: s for s in _sops()}
    battery_only = chunking.sop_section_chunks(sops["SOP-BAT-003"])[0]["content"]
    station_only = chunking.sop_section_chunks(sops["SOP-STN-003"])[0]["content"]
    both = chunking.sop_section_chunks(sops["SOP-BAT-001"])[0]["content"]
    assert battery_only.startswith("Asset type: Battery |")
    assert station_only.startswith("Asset type: Station |")
    assert both.startswith("Asset type: Battery, Station |")


def test_filename_must_encode_issue_type():
    import pytest
    with pytest.raises(ValueError):
        parse_sop_text("random-notes.md", "# x", {})
