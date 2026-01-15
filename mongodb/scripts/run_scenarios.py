"""Run scenario definitions and write outputs to out/scenarios."""

from __future__ import annotations

import json
from pathlib import Path

from json_flatten.csv_io import write_csv
from json_flatten.flattener import flatten_json, flatten_records
from json_flatten.scenarios import get_scenarios


def main() -> None:
    out_dir = Path("out/scenarios")
    out_dir.mkdir(parents=True, exist_ok=True)

    for scenario in get_scenarios():
        scenario_dir = out_dir / scenario.name
        scenario_dir.mkdir(parents=True, exist_ok=True)

        input_path = scenario_dir / "input.json"
        input_path.write_text(json.dumps(scenario.data, indent=2), encoding="utf-8")

        if scenario.mode == "records":
            records = flatten_records(
                scenario.data,
                explode_paths=scenario.explode_paths,
                list_policy=scenario.list_policy,
            )
        else:
            records = [flatten_json(scenario.data, list_policy=scenario.list_policy)]

        output_path = scenario_dir / "output.csv"
        write_csv(records, output_path)

        print(f"{scenario.name}: wrote {output_path}")


if __name__ == "__main__":
    main()
