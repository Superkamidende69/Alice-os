from pathlib import Path

from alice_os.secure_store import SecretStore


def test_secret_store_round_trip_and_clear(tmp_path: Path) -> None:
    store = SecretStore(tmp_path / "secrets" / "huggingface-token")

    assert store.get() is None
    store.set("hf_example_token")
    assert store.get() == "hf_example_token"
    assert store.path.read_bytes() != b"hf_example_token"

    store.clear()
    assert store.get() is None
