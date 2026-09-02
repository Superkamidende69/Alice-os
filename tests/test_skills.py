from alice_os.skills import get_skill, list_skills


def test_skill_catalog_has_unique_ids_and_safe_fallback() -> None:
    skills = list_skills()

    assert [skill["id"] for skill in skills] == [
        "general",
        "plan",
        "debug",
        "review",
        "implement",
    ]
    assert get_skill("review").read_only is True
    assert get_skill("unknown").id == "general"
