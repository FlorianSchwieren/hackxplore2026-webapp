from app.mapping import to_app_health_state, to_app_species


def test_species_mapping_to_flutter_sprite_enum() -> None:
    assert to_app_species("Quercus rubra", "Laubbaum") == "oak"
    assert to_app_species("Acer campestre", "Laubbaum") == "maple"
    assert to_app_species("Betula pendula", "Laubbaum") == "birch"
    assert to_app_species("Pinus sylvestris", "Nadelbaum") == "pine"
    assert to_app_species("Salix alba", "Laubbaum") == "willow"
    assert to_app_species("Tilia cordata", "Laubbaum") == "other"


def test_health_state_mapping_to_flutter_enum() -> None:
    assert to_app_health_state("thriving") == "healthy"
    assert to_app_health_state("healthy") == "healthy"
    assert to_app_health_state("thirsty") == "warning"
    assert to_app_health_state("overwatered") == "overmoisturized"
    assert to_app_health_state("critical") == "dead"
