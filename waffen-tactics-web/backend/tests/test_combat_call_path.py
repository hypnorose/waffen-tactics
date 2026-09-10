import ast
from pathlib import Path

from services.combat_service import run_combat_simulation


def test_web_route_delegates_combat_to_service_owner_without_direct_simulator_import():
    source_path = Path(__file__).parents[1] / "routes" / "game_combat.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert "CombatSimulator" not in imported_names
    assert "run_combat_simulation" in imported_names
    assert "run_combat_simulation" in called_names
    assert run_combat_simulation.__module__ == "services.combat_service"


def test_legacy_core_manager_uses_shared_owner_and_game_manager_has_no_second_simulator():
    root = Path(__file__).parents[3] / "waffen-tactics" / "src" / "waffen_tactics" / "services"
    manager_source = (root / "combat_manager.py").read_text(encoding="utf-8")
    game_manager_source = (root / "game_manager.py").read_text(encoding="utf-8")

    assert "from ..services.combat_shared import CombatSimulator" in manager_source
    assert "from ..services.combat import CombatSimulator" not in manager_source
    assert "from ..services.combat import CombatSimulator" not in game_manager_source


def test_production_sources_do_not_import_quarantined_combat_paths():
    """Keep the prototype damage path out of production combat imports."""
    repo_root = Path(__file__).parents[3]
    production_roots = [
        repo_root / "waffen-tactics" / "src" / "waffen_tactics",
        repo_root / "waffen-tactics-web" / "backend",
    ]
    forbidden = {
        "waffen_tactics.core.combat_core",
        "waffen_tactics.processors.attack",
    }
    quarantined_files = {
        repo_root / "waffen-tactics" / "src" / "waffen_tactics" / "core" / "combat_core.py",
        repo_root / "waffen-tactics" / "src" / "waffen_tactics" / "processors" / "attack.py",
    }
    violations = []

    for production_root in production_roots:
        for source_path in production_root.rglob("*.py"):
            if (
                source_path in quarantined_files
                or source_path.name.startswith("test")
                or "tests" in source_path.parts
            ):
                continue
            tree = ast.parse(source_path.read_text(encoding="utf-8-sig"), filename=str(source_path))
            for node in ast.walk(tree):
                imported = []
                if isinstance(node, ast.Import):
                    imported = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    imported = [
                        f"{module}.{alias.name}" if module else alias.name
                        for alias in node.names
                    ]

                for module_name in imported:
                    if any(
                        module_name == banned or module_name.startswith(f"{banned}.")
                        for banned in forbidden
                    ):
                        violations.append(f"{source_path}: {module_name}")

    assert not violations, "Production imports quarantined combat paths: " + "; ".join(violations)

    owner_source = (
        repo_root / "waffen-tactics" / "src" / "waffen_tactics" / "services" / "combat_shared.py"
    ).read_text(encoding="utf-8")
    assert "from .combat_simulator import CombatSimulator" in owner_source
