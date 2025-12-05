#!/usr/bin/env python3
import subprocess
import javalang
import os
import json
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Set


def read_file(path: str) -> str:
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def get_package(tree) -> Optional[str]:
    for _, node in tree.filter(javalang.tree.PackageDeclaration):
        return node.name
    return None


def is_primitive(t: str) -> bool:
    return t in {"boolean", "byte", "char", "short", "int", "long", "float", "double"}


def is_java_lang(t: str) -> bool:
    return t in {
        "Boolean", "Byte", "Character", "Short", "Integer", "Long",
        "Float", "Double", "String", "Object", "Class", "ClassLoader"
    }


def is_java_util(t: str) -> bool:
    return t in {
        "Collection", "List", "ArrayList", "LinkedList", "Map", "HashMap",
        "Set", "HashSet", "TreeSet", "Iterator", "Optional", "Date",
        "Calendar", "Locale"
    }


def is_java_time(t: str) -> bool:
    return t in {
        "LocalDate", "LocalDateTime", "LocalTime", "Instant", "Duration", "Period"
    }


def resolve_type(simple: str, imports: List[str], package: Optional[str], seen_types: Set[str]) -> str:
    """
    Resolve a simple type name to its fully qualified name.
    Resolution order:
      1. Primitive
      2. java.lang.*
      3. java.util.*
      4. java.time.*
      5. Same package
      6. Explicit imports
      7. Fallback → simple
    """
    is_arr = simple.endswith("[]")
    base = simple.rstrip("[]")

    # 1. Primitive
    if is_primitive(base):
        return simple

    # 2. java.lang
    if is_java_lang(base):
        fqn = f"java.lang.{base}"
        return f"{fqn}[]" if is_arr else fqn

    # 3. java.util
    if is_java_util(base):
        fqn = f"java.util.{base}"
        return f"{fqn}[]" if is_arr else fqn

    # 4. java.time
    if is_java_time(base):
        fqn = f"java.time.{base}"
        return f"{fqn}[]" if is_arr else fqn

    # 5. Same package
    if package:
        same_pkg_fqn = f"{package}.{base}"
        if same_pkg_fqn not in seen_types:
            return f"{same_pkg_fqn}[]" if is_arr else same_pkg_fqn

    # 6. Explicit imports
    for imp in imports:
        if imp.endswith("." + base):
            fqn = imp
            return f"{fqn}[]" if is_arr else fqn

    # 7. Fallback
    return simple


def get_full_method_name(class_name: str, package: Optional[str], method_name: str,
                         params: List[Tuple[str, str]], imports: List[str], seen: Set[str]) -> str:
    param_fqns = [resolve_type(p_type, imports, package, seen)
                  for p_type, _ in params]
    qualified_class = f"{package}.{class_name}" if package else class_name
    return f"{qualified_class}.{method_name}({','.join(param_fqns)})"


def parse_java_file(path: str) -> Dict[str, Tuple[int, int, str, str, List[Tuple[str, str]], str]]:
    try:
        tree = javalang.parse.parse(read_file(path))
    except Exception as e:
        print(f"[ERROR] Parse {path}: {e}")
        return {}

    package = get_package(tree)
    imports = [node.path for _, node in tree.filter(javalang.tree.Import)]
    seen_types: Set[str] = set()
    methods: Dict[str, Tuple[int, int, str,
                             str, List[Tuple[str, str]], str]] = {}

    for _, class_node in tree.filter(javalang.tree.ClassDeclaration):
        class_fqn = f"{package}.{class_node.name}" if package else class_node.name
        seen_types.add(class_fqn)

        for member in (class_node.body or []):
            if not isinstance(member, javalang.tree.MethodDeclaration):
                continue
            if not member.position or not member.body or not member.name:
                continue

            start = member.position.line
            end = member.body[-1].position.line if member.body else start

            params = []
            for p in member.parameters:
                p_type = getattr(p.type, 'name', None)
                if p_type is None and hasattr(p.type, 'type'):
                    p_type = getattr(p.type.type, 'name', None)
                if p_type is None:
                    p_type = "Object"
                if getattr(p.type, 'dimensions', 0):
                    p_type += "[]" * len(p.type.dimensions)
                params.append((p_type, p.name))

            full = get_full_method_name(
                class_node.name, package, member.name, params, imports, seen_types)
            methods[full] = (start, end, class_node.name,
                             package, params, full)

    print(f"[OK] {len(methods)} methods → {os.path.basename(path)}")
    return methods


def git_log_lines(file_path: str, start: int, end: int) -> Tuple[int, int]:
    cmd = ['git', 'log', '--oneline', f'-L{start},{end}:{file_path}']
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        if any(x in result.stderr for x in ["no matches", "fatal: file"]):
            return 0, 0
        print(f"[WARN] git {file_path}:{start}-{end}: {result.stderr.strip()}")
        return 0, 0

    lines = result.stdout.strip().splitlines()
    total = len(lines)
    fixes = sum(1 for l in lines if any(k in l.lower()
                for k in {"fix", "bug", "issue", "patch", "resolve"}))
    return total, fixes


def analyze_file(path: str) -> List[dict]:
    methods = parse_java_file(path)
    out = []
    for full, (s, e, _, _, _, _) in methods.items():
        ch, fx = git_log_lines(path, s, e)
        ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        hid = f"{full}_{ts}"
        out.append({
            "full_name": full,
            "num_changes": ch,
            "num_fixes": fx,
            "changespot_id": hid
        })
    return out


def build_graph(data: List[dict]) -> dict:
    nodes: List[dict] = []
    edges: List[dict] = []
    seen = set()

    for d in data:
        f = d["full_name"]
        hid = d["changespot_id"]
        ch = d["num_changes"]
        fx = d["num_fixes"]

        nodes.append({"type": "Method", "fullName": f})

        if hid not in seen:
            nodes.append({
                "type": "Changespot",
                "numOfChanges": ch,
                "numOfFixes": fx,
                "id": hid
            })
            seen.add(hid)

        edges.append({
            "relationName": "Changed",
            "from": {"nodeType": "Method", "propertyName": "fullName", "propertyValue": f},
            "to":   {"nodeType": "Changespot", "propertyName": "id", "propertyValue": hid}
        })

    return {"probeName": "Changespot", "nodes": nodes, "edges": edges}


def save_json(path: str, obj: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    print(f"[OK] Saved → {path}")


def main():
    p = argparse.ArgumentParser(
        description="Changespot Analyzer – refined FQN resolution")
    p.add_argument("--src", required=True, help="src/main/java")
    p.add_argument("--out", required=True, help="output.json")
    p.add_argument("--git-root", default=".", help="git repo root")
    args = p.parse_args()

    git_root = os.path.abspath(args.git_root)
    src_dir = os.path.abspath(args.src)
    os.chdir(git_root)

    java_files = [
        os.path.relpath(os.path.join(r, f), git_root)
        for r, _, fs in os.walk(src_dir)
        for f in fs if f.endswith(".java")
    ]

    print(f"[INFO] {len(java_files)} Java files")

    all_data: List[dict] = []
    for fp in java_files:
        try:
            all_data.extend(analyze_file(fp))
        except Exception as e:
            print(f"[ERROR] {fp}: {e}")

    graph = build_graph(all_data)
    save_json(args.out, graph)


if __name__ == "__main__":
    main()
