from app.seed.funny_names import funny_tree_name


def test_funny_tree_name_is_deterministic() -> None:
    assert funny_tree_name(12345) == funny_tree_name(12345)
    assert funny_tree_name(12345) != funny_tree_name(67890)


def test_funny_tree_name_is_non_empty() -> None:
    name = funny_tree_name(999)
    assert " " in name
    assert len(name) > 3
