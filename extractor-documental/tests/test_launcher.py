"""Cache de instalación y runtimes: sin red, navegador ni servidor en estas pruebas."""
from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from bsg_extractor import launcher


def test_prepare_reuses_installation_and_rebuilds_only_changed_sources(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(launcher, "_node_and_npm", lambda: ("node", ["node", "npm-cli.js"]))
    (tmp_path / "pyproject.toml").write_text("[project]\nname='fixture'", encoding="utf-8")
    lock = tmp_path / "requirements.lock.txt"
    lock.write_text("pytest==9.1.1\n", encoding="ascii")
    environment = tmp_path / ".venv"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    python.parent.mkdir(parents=True)
    python.write_bytes(b"dummy runtime; never executed")
    web = tmp_path / "web"
    (web / "src").mkdir(parents=True)
    (web / "package.json").write_text("{}", encoding="ascii")
    (web / "package-lock.json").write_text("{}", encoding="ascii")
    source = web / "src" / "app.tsx"
    source.write_text("const fixture = 1", encoding="ascii")
    commands = []

    def run(command, *, cwd=None):
        commands.append(command)
        if "ci" in command:
            (web / "node_modules").mkdir(exist_ok=True)
        if "build" in command:
            (web / "dist").mkdir(exist_ok=True)
            (web / "dist" / "index.html").write_text("fixture", encoding="ascii")
            (web / "tsconfig.tsbuildinfo").write_text("generated fixture", encoding="ascii")

    monkeypatch.setattr(launcher, "_run", run)
    assert launcher.prepare() == python
    assert len(commands) == 4
    assert "requirements.lock.txt" in commands[0]
    assert "--no-build-isolation" in commands[1] and "--no-deps" in commands[1]
    commands.clear()
    assert launcher.prepare() == python
    assert commands == []
    source.write_text("const fixture = 2", encoding="ascii")
    launcher.prepare()
    assert len(commands) == 1 and commands[0][-2:] == ["run", "build"]
    commands.clear()
    lock.write_text("pytest==9.1.1\n# dependency lock changed\n", encoding="ascii")
    launcher.prepare()
    assert len(commands) == 2 and all("pip" in command for command in commands)


@pytest.mark.parametrize("version,allowed", [("v20.18.0", False), ("v20.19.0", True), ("v21.9.0", False),
                                             ("v22.11.0", False), ("v22.12.0", True), ("v22.17.0", True),
                                             ("v24.0.0", True), ("invalid", False)])
def test_node_engine_compatible_versions(version, allowed, monkeypatch):
    monkeypatch.setattr(launcher.shutil, "which", lambda name: "node" if name == "node" else "npm")
    monkeypatch.setattr(launcher.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout=version))
    if allowed:
        assert launcher._node_and_npm()[0] == "node"
    else:
        with pytest.raises(RuntimeError):
            launcher._node_and_npm()


def test_running_app_reopens_without_reinstalling_or_restarting(monkeypatch):
    opened = []
    monkeypatch.setattr(launcher, "_already_running", lambda: True)
    monkeypatch.setattr(launcher.webbrowser, "open", opened.append)

    def forbidden(*args, **kwargs):
        pytest.fail("Una instancia ya activa no debe prepararse ni reiniciarse")

    monkeypatch.setattr(launcher, "prepare", forbidden)
    monkeypatch.setattr(launcher, "_run", forbidden)
    assert launcher.main() == 0
    assert opened == ["http://127.0.0.1:8765"]
