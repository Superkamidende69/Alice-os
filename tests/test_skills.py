import pytest

from alice_os.skills import AgentSkill, SkillStore, get_skill, list_skills


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


def test_custom_skills_persist_and_built_ins_are_protected(tmp_path) -> None:
    store = SkillStore(tmp_path)
    saved = store.upsert(
        AgentSkill(
            id="python-engineer",
            name="Python engineer",
            description="Build Python features.",
            instructions="Inspect first, then implement and test.",
        )
    )

    assert saved.id == "python-engineer"
    assert SkillStore(tmp_path).get("python-engineer").name == "Python engineer"
    with pytest.raises(ValueError, match="cannot be replaced"):
        store.upsert(saved.__class__("general", "No", "No", "No"))
    store.delete("python-engineer")
    assert SkillStore(tmp_path).get("python-engineer").id == "general"
