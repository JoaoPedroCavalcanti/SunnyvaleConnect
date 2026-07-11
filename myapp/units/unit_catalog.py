"""Pure helpers: infer floors from apartment codes and group units for the UI."""

from __future__ import annotations

from units.models import Unit

# Brazilian bulk-provision pattern: ``{floor}{door}`` with a 2-digit door
# (e.g. floor 15 + ``01`` → ``1501``). Shorter codes are treated as flat
# house / lot numbers without a floor.
_DOOR_WIDTH = 2


def parse_apartment(apartment: str) -> tuple[str | None, str]:
    """Return ``(floor, door_label)``.

    ``floor`` is ``None`` when the code is not a floor+door pattern.
    """
    raw = (apartment or "").strip()
    if not raw.isdigit() or len(raw) <= _DOOR_WIDTH:
        return None, raw
    floor = raw[:-_DOOR_WIDTH].lstrip("0") or "0"
    door = raw[-_DOOR_WIDTH:]
    return floor, door


def _sort_key_numeric_str(value: str):
    text = (value or "").strip()
    if text.isdigit():
        return (0, int(text), text)
    return (1, text.casefold(), text)


def _unit_item(entry: dict) -> dict:
    unit = entry["unit"]
    floor, label = parse_apartment(unit.apartment)
    if unit.kind == Unit.Kind.NAMED:
        label = unit.name
        floor = None
    return {
        "id": unit.id,
        "kind": unit.kind,
        "name": unit.name,
        "apartment": unit.apartment,
        "block": unit.block,
        "label": label,
        "floor": floor,
        "display_name": unit.display_name(),
        "is_occupied": bool(entry.get("is_occupied")),
    }


def _matches_filters(
    item: dict,
    *,
    block: str | None,
    floor: str | None,
    apartment: str | None,
    name: str | None,
) -> bool:
    if block is not None:
        if (item["block"] or "").casefold() != block.casefold():
            return False
    if floor is not None:
        if item["floor"] is None or item["floor"].casefold() != floor.casefold():
            return False
    if apartment is not None:
        needle = apartment.strip().casefold()
        apt = (item["apartment"] or "").casefold()
        label = (item["label"] or "").casefold()
        matched = needle in (apt, label) or (
            (apt.lstrip("0") or "0") == (needle.lstrip("0") or "0")
        )
        if not matched:
            return False
    if name is not None:
        if (item["name"] or "").casefold() != name.strip().casefold():
            return False
    return True


def detect_layout(items: list[dict]) -> str:
    """``blocks`` | ``floors`` | ``flat`` based on the unit mix."""
    has_block = any(i["block"] for i in items if i["kind"] != Unit.Kind.NAMED)
    has_floor = any(i["floor"] is not None for i in items)
    if has_block:
        return "blocks"
    if has_floor:
        return "floors"
    return "flat"


def build_catalog(
    occupied_entries: list[dict],
    *,
    condominium_id: int,
    condominium_code: str,
    block: str | None = None,
    floor: str | None = None,
    apartment: str | None = None,
    name: str | None = None,
) -> dict:
    items = [_unit_item(e) for e in occupied_entries]
    items = [
        i
        for i in items
        if _matches_filters(
            i, block=block, floor=floor, apartment=apartment, name=name
        )
    ]

    named = sorted(
        [i for i in items if i["kind"] == Unit.Kind.NAMED],
        key=lambda i: (i["name"] or "").casefold(),
    )
    structured = [i for i in items if i["kind"] != Unit.Kind.NAMED]
    layout = detect_layout(structured) if structured else (
        "flat" if named else "flat"
    )
    # Prefer blocks/floors from the filtered structured set.
    if any(i["block"] for i in structured):
        layout = "blocks"
    elif any(i["floor"] is not None for i in structured):
        layout = "floors"
    else:
        layout = "flat"

    blocks_out: list[dict] = []
    floors_out: list[dict] = []
    flat_out: list[dict] = []

    if layout == "blocks":
        by_block: dict[str, list[dict]] = {}
        for item in structured:
            key = item["block"] or ""
            by_block.setdefault(key, []).append(item)
        for block_key in sorted(by_block.keys(), key=lambda b: b.casefold()):
            floors_out_block = _group_floors(by_block[block_key])
            blocks_out.append({"block": block_key, "floors": floors_out_block})
    elif layout == "floors":
        floors_out = _group_floors(structured)
    else:
        flat_out = sorted(
            structured,
            key=lambda i: _sort_key_numeric_str(i["apartment"] or i["label"]),
        )

    return {
        "condominium_id": condominium_id,
        "condominium_code": condominium_code,
        "layout": layout,
        "blocks": blocks_out,
        "floors": floors_out,
        "units": flat_out,
        "named": named,
    }


def _group_floors(items: list[dict]) -> list[dict]:
    by_floor: dict[str | None, list[dict]] = {}
    for item in items:
        by_floor.setdefault(item["floor"], []).append(item)

    floored = [(f, us) for f, us in by_floor.items() if f is not None]
    floored.sort(key=lambda pair: _sort_key_numeric_str(pair[0]))

    result: list[dict] = []
    for floor_key, units in floored:
        units_sorted = sorted(
            units,
            key=lambda i: _sort_key_numeric_str(i["label"] or i["apartment"]),
        )
        result.append({"floor": floor_key, "units": units_sorted})

    # Units that somehow have a block but no parseable floor sit under "".
    leftover = by_floor.get(None) or []
    if leftover:
        result.append(
            {
                "floor": "",
                "units": sorted(
                    leftover,
                    key=lambda i: _sort_key_numeric_str(
                        i["apartment"] or i["label"]
                    ),
                ),
            }
        )
    return result


def build_filter_options(
    occupied_entries: list[dict],
    *,
    condominium_id: int,
    condominium_code: str,
) -> dict:
    items = [_unit_item(e) for e in occupied_entries]
    structured = [i for i in items if i["kind"] != Unit.Kind.NAMED]
    named = [i for i in items if i["kind"] == Unit.Kind.NAMED]
    layout = detect_layout(structured) if structured else "flat"

    blocks = sorted(
        {i["block"] for i in structured if i["block"]},
        key=lambda b: b.casefold(),
    )
    floors = sorted(
        {i["floor"] for i in structured if i["floor"] is not None},
        key=_sort_key_numeric_str,
    )
    floors_by_block: dict[str, list[str]] = {}
    for item in structured:
        if not item["block"] or item["floor"] is None:
            continue
        floors_by_block.setdefault(item["block"], set()).add(item["floor"])
    floors_by_block_out = {
        blk: sorted(vals, key=_sort_key_numeric_str)
        for blk, vals in sorted(
            floors_by_block.items(), key=lambda kv: kv[0].casefold()
        )
    }

    if layout == "flat":
        apartment_options = sorted(
            {i["apartment"] for i in structured if i["apartment"]},
            key=_sort_key_numeric_str,
        )
    else:
        # Flat leftovers only (e.g. mixed condo); floor grids use block/floor.
        apartment_options = sorted(
            {
                i["apartment"]
                for i in structured
                if i["apartment"] and i["floor"] is None
            },
            key=_sort_key_numeric_str,
        )
    names = sorted({i["name"] for i in named if i["name"]}, key=str.casefold)

    return {
        "condominium_id": condominium_id,
        "condominium_code": condominium_code,
        "layout": layout,
        "filters": {
            "block": {"enabled": bool(blocks), "options": blocks},
            "floor": {
                "enabled": bool(floors),
                "options": floors,
                "options_by_block": floors_by_block_out,
            },
            "apartment": {
                "enabled": bool(apartment_options),
                "options": apartment_options,
            },
            "name": {"enabled": bool(names), "options": names},
        },
    }
