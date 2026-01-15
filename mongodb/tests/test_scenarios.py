from json_flatten.scenarios import get_scenarios


def test_scenarios_have_names() -> None:
    scenarios = get_scenarios()
    assert scenarios
    assert all(scenario.name for scenario in scenarios)
