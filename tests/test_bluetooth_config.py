from pathlib import Path

from raingel.bluetooth_config import controller_status, read_controller_mode, set_controller_mode_le


def test_read_controller_mode_ignores_commented_value(tmp_path: Path):
    path = tmp_path / "main.conf"
    path.write_text("[General]\n#ControllerMode = dual\n", encoding="utf-8")

    assert read_controller_mode(path) is None
    assert controller_status(path)["isLe"] is False


def test_set_controller_mode_uncomments_existing_value(tmp_path: Path):
    path = tmp_path / "main.conf"
    backup = tmp_path / "main.conf.vc-ble-light-controller.bak"
    path.write_text("[General]\n#ControllerMode = dual\n", encoding="utf-8")

    status = set_controller_mode_le(path, backup, restart_bluetooth=False)

    assert status["isLe"] is True
    assert status["changed"] is True
    assert path.read_text(encoding="utf-8") == "[General]\nControllerMode = le\n"
    assert backup.read_text(encoding="utf-8") == "[General]\n#ControllerMode = dual\n"


def test_set_controller_mode_inserts_in_general_section(tmp_path: Path):
    path = tmp_path / "main.conf"
    backup = tmp_path / "main.conf.vc-ble-light-controller.bak"
    path.write_text("[General]\nName = test\n", encoding="utf-8")

    set_controller_mode_le(path, backup, restart_bluetooth=False)

    assert path.read_text(encoding="utf-8") == "[General]\nControllerMode = le\nName = test\n"
