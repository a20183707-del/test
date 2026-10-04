"""Inicio reproducible Windows sin instalar runtimes ni guardar credenciales."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import urllib.error
import urllib.request
import venv
import webbrowser

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCAL_URL = "http://127.0.0.1:8765"


def _run(command: list[str], *, cwd: Path = PROJECT_ROOT) -> None:
    result = subprocess.run(command, cwd=cwd, check=False)
    if result.returncode:
        raise RuntimeError("Falló un paso de instalación o compilación. Revisa el mensaje anterior.")


def _digest(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(str(path.relative_to(PROJECT_ROOT)).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _node_and_npm() -> tuple[str, list[str]]:
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Falta Node.js 20.19+, 22.12+ o posterior. Instálalo y vuelve a ejecutar iniciar.bat.")
    version = subprocess.run([node, "--version"], capture_output=True, text=True, check=True).stdout.strip()
    parsed = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", version)
    if parsed is None:
        raise RuntimeError("No se pudo comprobar la versión de Node.js.")
    major, minor = map(int, parsed.group(1, 2))
    if not (major == 20 and minor >= 19 or major == 22 and minor >= 12 or major > 22):
        raise RuntimeError("Se requiere Node.js 20.19+, 22.12+ o posterior para compilar la interfaz.")
    # Ejecutar npm con Node evita las restricciones de npm.ps1 de PowerShell.
    npm_cli = Path(node).parent / "node_modules" / "npm" / "bin" / "npm-cli.js"
    if npm_cli.is_file():
        return node, [node, str(npm_cli)]
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        raise RuntimeError("No se encontró npm. Reinstala Node.js con npm incluido.")
    return node, [npm]


def prepare() -> Path:
    if sys.version_info < (3, 11):
        raise RuntimeError("Se requiere Python 3.11 o posterior.")
    _, npm_command = _node_and_npm()
    environment = PROJECT_ROOT / ".venv"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        print("Creando entorno Python local…", flush=True)
        venv.EnvBuilder(with_pip=True).create(environment)
    dependency_digest = _digest([PROJECT_ROOT / "pyproject.toml", PROJECT_ROOT / "requirements.lock.txt"])
    dependency_marker = environment / ".bsg-dependencies-hash"
    if not dependency_marker.is_file() or dependency_marker.read_text(encoding="ascii") != dependency_digest:
        print("Instalando dependencias Python…", flush=True)
        _run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "-r", "requirements.lock.txt"])
        _run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "--no-deps",
              "--no-build-isolation", "-e", "."])
        dependency_marker.write_text(dependency_digest, encoding="ascii")
    web = PROJECT_ROOT / "web"
    if not (web / "package-lock.json").is_file():
        raise RuntimeError("Falta web/package-lock.json. Recupera el repositorio completo antes de iniciar.")
    sources = [path for path in web.rglob("*") if path.is_file() and not path.name.startswith(".bsg-")
               and not path.name.endswith(".tsbuildinfo")
               and not set(path.relative_to(web).parts).intersection({"node_modules", "dist", ".git"})]
    build_digest = _digest(sources)
    build_marker = web / ".bsg-build-hash"
    npm_digest = _digest([web / "package.json", web / "package-lock.json"])
    npm_marker = web / ".bsg-dependencies-hash"
    if not (web / "node_modules").is_dir() or not npm_marker.is_file() or npm_marker.read_text(encoding="ascii") != npm_digest:
        print("Instalando dependencias de la interfaz…", flush=True)
        _run(npm_command + ["ci", "--no-audit", "--no-fund"], cwd=web)
        npm_marker.write_text(npm_digest, encoding="ascii")
    needs_build = not (web / "dist" / "index.html").is_file() or not build_marker.is_file() or build_marker.read_text(encoding="ascii") != build_digest
    if needs_build:
        print("Compilando interfaz…", flush=True)
        _run(npm_command + ["run", "build"], cwd=web)
        build_marker.write_text(build_digest, encoding="ascii")
    return python


def _already_running() -> bool:
    try:
        with urllib.request.urlopen(LOCAL_URL + "/api/health", timeout=1) as response:
            result = json.loads(response.read(4096))
        return result.get("application") == "bsg-extractor" and result.get("ok") is True
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return False


def main() -> int:
    try:
        if _already_running():
            print("La aplicación BSG ya está funcionando en " + LOCAL_URL, flush=True)
            webbrowser.open(LOCAL_URL)
            return 0
        python = prepare()
        print("\nAplicación local: " + LOCAL_URL + "\nDeja esta ventana abierta. Ctrl+C detiene el servidor.", flush=True)
        threading.Timer(2, lambda: webbrowser.open(LOCAL_URL)).start()
        # Sin reload ni acceso remoto. Access logs desactivados; la clave sólo viaja en POST.
        _run([str(python), "-m", "uvicorn", "bsg_extractor.server:app", "--host", "127.0.0.1",
              "--port", "8765", "--no-access-log", "--log-level", "warning"])
        return 0
    except KeyboardInterrupt:
        print("\nServidor detenido. La sesión en memoria se elimina.", flush=True)
        return 0
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        print("\nNo se pudo iniciar BSG: " + str(error), file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
