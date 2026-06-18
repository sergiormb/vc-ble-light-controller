from pathlib import Path

from raingel.config import ConfigStore, LampState


def test_config_roundtrip(tmp_path: Path):
    path = tmp_path / "lights.json"
    store = ConfigStore(path)
    lamps = [
        LampState(
            address="1C:D5:EA:C9:C9:9A",
            name="Salon",
            powered=True,
            color=(255, 60, 60),
            brightness=80,
        )
    ]

    store.save(lamps)
    loaded = store.load()

    assert loaded == lamps


def test_invalid_config_returns_empty(tmp_path: Path):
    path = tmp_path / "lights.json"
    path.write_text("{bad json", encoding="utf-8")

    assert ConfigStore(path).load() == []


def test_legacy_config_is_loaded_and_migrated(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    legacy_dir = tmp_path / ".config" / "raingel"
    legacy_dir.mkdir(parents=True)
    legacy_path = legacy_dir / "lights.json"
    legacy_path.write_text(
        '{"lamps":[{"address":"AA:BB","name":"Legacy","powered":true,"color":[1,2,3],"brightness":44}]}',
        encoding="utf-8",
    )
    new_path = tmp_path / ".config" / "vc-ble-light-controller" / "lights.json"

    loaded = ConfigStore(new_path).load()

    assert loaded[0].address == "AA:BB"
    assert loaded[0].name == "Legacy"
    assert new_path.exists()
