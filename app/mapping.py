def title_for_tree(name: str | None, external_id: int) -> str:
    return name or f"Baum #{external_id}"


def to_app_species(artlat: str | None, baumart_allgemein: str | None) -> str:
    latin = (artlat or "").lower()
    category = (baumart_allgemein or "").lower()
    if latin.startswith("quercus"):
        return "oak"
    if latin.startswith("acer"):
        return "maple"
    if latin.startswith("betula"):
        return "birch"
    if latin.startswith("pinus") or "nadelbaum" in category:
        return "pine"
    if latin.startswith("salix"):
        return "willow"
    return "other"


def to_app_health_state(health_state: str | None) -> str | None:
    if health_state in {"thriving", "healthy"}:
        return "healthy"
    if health_state == "thirsty":
        return "warning"
    if health_state == "overwatered":
        return "overmoisturized"
    if health_state == "critical":
        return "dead"
    return None
