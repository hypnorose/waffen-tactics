#!/usr/bin/env python3
"""Generate a PlantUML dependency diagram from local Python imports.

Usage:
  python3 tools/gen_plantuml_deps.py -o plantuml/deps.puml

This scans .py files in the repository (excluding common folders), parses imports,
tries to resolve them to local modules, and emits a PlantUML file with components
and dependency arrows.
"""
import os
import ast
import argparse
from collections import defaultdict

IGNORE_DIRS = {'.git', '__pycache__', 'htmlcov', 'docs', 'experiments', 'venv', '.venv', 'node_modules'}


def find_python_files(root):
    py_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # prune ignored dirs
        parts = set(dirpath.split(os.sep))
        if parts & IGNORE_DIRS:
            continue
        for fname in filenames:
            if fname.endswith('.py'):
                py_files.append(os.path.join(dirpath, fname))
    return py_files


def module_name_from_path(root, path):
    rel = os.path.relpath(path, root)
    if rel.startswith('..'):
        return None
    if os.path.basename(path) == '__init__.py':
        mod = os.path.dirname(rel)
    else:
        mod = rel[:-3]
    mod = mod.replace(os.sep, '.')
    mod = mod.strip('.')
    return mod


def parse_imports(path, source_mod):
    with open(path, 'rb') as f:
        try:
            tree = ast.parse(f.read(), filename=path)
        except Exception:
            return set(), set()

    imports = set()
    rel_imports = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            # handle relative imports
            if node.level and source_mod:
                base_parts = source_mod.split('.')[:-node.level]
                if node.module:
                    target = '.'.join(base_parts + [node.module]) if base_parts else node.module
                else:
                    target = '.'.join(base_parts) if base_parts else ''
                if target:
                    rel_imports.add(target)
            elif node.module:
                imports.add(node.module)
    return imports, rel_imports


def build_graph(root, package=None):
    py_files = find_python_files(root)
    modules = {}
    for p in py_files:
        mod = module_name_from_path(root, p)
        if mod:
            modules[mod] = p

    # If a package filter is provided, keep only modules under that package
    if package:
        modules = {k: v for k, v in modules.items() if k == package or k.startswith(package + '.')}

    edges = set()
    for mod, path in modules.items():
        imports, rels = parse_imports(path, mod)
        all_imps = set()
        all_imps.update([imp.split('.')[0] for imp in imports])
        all_imps.update(rels)

        for imp in all_imps:
            # match to local module candidates
            for candidate in modules:
                if candidate == imp or candidate.startswith(imp + '.') or imp.startswith(candidate + '.'):
                    if candidate != mod:
                        edges.add((mod, candidate))
    return modules.keys(), edges


def plantuml_id(name):
    return name.replace('.', '_').replace('-', '_')


def emit_plantuml(modules, edges, outpath):
    lines = []
    lines.append('@startuml')
    lines.append('skinparam componentStyle rectangle')
    lines.append('')
    # define components
    for m in sorted(modules):
        id_ = plantuml_id(m)
        lines.append(f'component "{m}" as {id_}')
    lines.append('')
    # relations
    for a, b in sorted(edges):
        lines.append(f'{plantuml_id(a)} --> {plantuml_id(b)}')
    lines.append('')
    lines.append('@enduml')

    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def main():
    parser = argparse.ArgumentParser(description='Generate PlantUML dependencies from Python imports')
    parser.add_argument('-o', '--output', default='plantuml/deps.puml')
    parser.add_argument('--root', default='.')
    parser.add_argument('--package', default=None, help='Only include modules under this package (e.g. waffen_tactics)')
    args = parser.parse_args()

    modules, edges = build_graph(args.root, package=args.package)
    emit_plantuml(modules, edges, args.output)
    print('Wrote', args.output)


if __name__ == '__main__':
    main()
