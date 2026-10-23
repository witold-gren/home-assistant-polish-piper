"""Audit pl_tts against real Home Assistant data.

Builds the sentences HA would speak for each entity ("<name>: <state> <unit>.")
and reports where normalize() left digits, unit symbols or other written forms.

Data source (one of):
  --api http://192.168.1.10:8123 --token-file hass_token   (REST /api/states)
  --states ha_states.json                                (export: list of
        {"id", "name", "state", "unit"} - e.g. from .storage/core.restore_state)

    python tools/ha_audit.py --api http://192.168.1.10:8123 --token-file ~/hass_token

Run it inside the Piper image (Morfeusz is there):
    docker run --rm --entrypoint bash -v "$PWD:/w" local/polish-piper:2.5.2 \
        -c "cd /w && /usr/src/.venv/bin/python3 tools/ha_audit.py --api ... --token-file ..."
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pl_tts import normalize  # noqa: E402

SKIP_STATES = {"", "unknown", "unavailable", "on", "off", "home", "not_home", "idle", "None"}
LEFTOVER = re.compile(r"\d|[°%/×_@#]|\b(?:[A-Z]{2,}|[a-z]+[A-Z]\w*)\b")


def load(args: argparse.Namespace) -> list[dict]:
    if args.states:
        data = json.loads(Path(args.states).read_text("utf-8"))
        return data["states"] if isinstance(data, dict) else data
    token = Path(args.token_file).expanduser().read_text().strip()
    req = urllib.request.Request(f"{args.api.rstrip('/')}/api/states", headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = json.load(resp)
    return [
        {"id": s["entity_id"], "name": s["attributes"].get("friendly_name"), "state": s["state"],
         "unit": s["attributes"].get("unit_of_measurement")}
        for s in raw
    ]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--api")
    p.add_argument("--token-file")
    p.add_argument("--states")
    p.add_argument("--limit", type=int, default=3, help="examples per problem pattern")
    args = p.parse_args()
    states = load(args)


    groups: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
    total = 0
    for s in states:
        state = str(s.get("state", ""))
        if state in SKIP_STATES:
            continue
        unit = s.get("unit") or ""
        sentence = f"{state} {unit}".strip()
        total += 1
        spoken = normalize(sentence)
        left = LEFTOVER.findall(spoken)
        if left:
            key = re.sub(r"\d", "9", sentence)
            key = re.sub(r"[a-ząćęłńóśźż]{3,}", "a", key)[:50]
            groups[key].append((s["id"], f"{sentence!r} -> {spoken!r}"))
    print(f"{total} entity states checked, {sum(map(len, groups.values()))} with leftovers in {len(groups)} patterns\n")
    for key, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        print(f"[{len(items)}] {key!r}")
        for eid, line in items[: args.limit]:
            print(f"    {eid}: {line}")


if __name__ == "__main__":
    main()
