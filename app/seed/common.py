from uuid import NAMESPACE_URL, UUID, uuid5

SEED_NAMESPACE = uuid5(NAMESPACE_URL, "https://baumpate.demo/hackxplore")


def seed_uuid(name: str) -> UUID:
    return uuid5(SEED_NAMESPACE, name)
