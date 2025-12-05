#!/usr/bin/env python3
import json
import re
import os
import sys
import argparse


TYPE_MAP = {
    "Integer": "java.lang.Integer",
    "String": "java.lang.String",
    "Boolean": "java.lang.Boolean",
    "Long": "java.lang.Long",
    "Double": "java.lang.Double",
    "Float": "java.lang.Float",
    "Short": "java.lang.Short",
    "Byte": "java.lang.Byte",
    "Character": "java.lang.Character",
    "Object": "java.lang.Object",
    "LocalDate": "java.time.LocalDate",
    "Date": "java.util.Date",
    "Locale": "java.util.Locale",
    "List": "java.util.List",
    "Map": "java.util.Map",
    "Set": "java.util.Set",
    "BindingResult": "org.springframework.validation.BindingResult",
    "Model": "org.springframework.ui.Model",
}

PRIMITIVE_TYPES = {"int", "boolean", "long", "double", "float", "short", "byte", "char"}


def normalise_method_name(name: str) -> str:
    return re.sub(r'\s+', ' ', name.strip())


def extract_java_fqn(rel_path: str):
    java_file = os.path.basename(rel_path)
    class_name, _ = os.path.splitext(java_file)

    m = re.search(r'((?:org|com|net|io|edu)(?:[\\/][\w\d_]+)+)[\\/]([\w\d_]+)\.java$', rel_path)
    if m:
        package_path = m.group(1)
    else:
        m2 = re.search(r'src[\\/]main[\\/]java[\\/](.*)[\\/]([\w\d_]+)\.java$', rel_path)
        package_path = m2.group(1) if m2 else os.path.dirname(rel_path)

    package = package_path.replace("/", ".").replace("\\", ".").strip(".")
    return package, class_name


def qualify_argument(arg: str, current_package: str) -> str:
    arg = arg.strip()
    if not arg:
        return arg
    if arg in PRIMITIVE_TYPES:
        return arg
    if arg in TYPE_MAP:
        return TYPE_MAP[arg]
    if "." in arg:
        return arg
    if arg and arg[0].isupper():
        return f"{current_package}.{arg}"
    return f"java.lang.{arg}"


def parse_pmd_report(pmd_report_path: str, source_code_dir: str):
    nodes, edges = [], []
    class_node_by_fqn = {}
    method_node_by_fqn = {}

    with open(pmd_report_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue

            m = re.match(
                r"^(?:\./)?(?P<file>[\S]+):(?P<line>\d+):\s+(?P<rule>\w+):\s+(?P<msg>.+)$",
                line,
            )
            if not m:
                continue

            rel_path = m.group("file")
            line_no = int(m.group("line")
            rule = m.group("rule")
            message = m.group("msg").strip()

            if rule != "CyclomaticComplexity":
                continue

            issue_id = f"{rel_path}:{line_no}:{rule}:{message}"
            issue_node = {"type": "Issue", "id": issue_id, "description": message}
            nodes.append(issue_node)

            abs_path = os.path.normpath(os.path.join(source_code_dir, rel_path))
            if not os.path.exists(abs_path):
                continue

            package, class_name = extract_java_fqn(rel_path)

            method_match = re.search(r"The method ['\"`]([^'\"`]+)['\"`] has", message)
            if method_match:
                raw_method = method_match.group(1)
                method_name = normalise_method_name(raw_method)

                m_args = re.match(r"([^(]+)\(([^)]*)\)", method_name)
                if m_args:
                    name_only, args_str = m_args.groups()
                    args = [a.strip() for a in args_str.split(",") if a.strip()]
                    fq_args = [qualify_argument(a, package) for a in args]
                    method_name = f"{name_only}({','.join(fq_args)})"

                fqn_method = f"{package}.{class_name}.{method_name}"

                if fqn_method not in method_node_by_fqn:
                    method_node = {"type": "Method", "fullName": fqn_method}
                    method_node_by_fqn[fqn_method] = method_node
                    nodes.append(method_node)

                edges.append({
                    "relationName": "HASISSUE",
                    "from": {"nodeType": "Method", "propertyName": "fullName", "propertyValue": fqn_method},
                    "to": {"nodeType": "Issue", "propertyName": "id", "propertyValue": issue_id},
                })
                continue

            class_match = re.search(r"The class ['\"`]([^'\"`]+)['\"`] has", message)
            if class_match:
                fqn_class = f"{package}.{class_name}"
                if fqn_class not in class_node_by_fqn:
                    class_node = {"type": "Class", "fullName": fqn_class}
                    class_node_by_fqn[fqn_class] = class_node
                    nodes.append(class_node)

                edges.append({
                    "relationName": "HASISSUE",
                    "from": {"nodeType": "Class", "propertyName": "fullName", "propertyValue": fqn_class},
                    "to": {"nodeType": "Issue", "propertyName": "id", "propertyValue": issue_id},
                })
                continue

            fqn_class = f"{package}.{class_name}"
            if fqn_class not in class_node_by_fqn:
                class_node = {"type": "Class", "fullName": fqn_class}
                class_node_by_fqn[fqn_class] = class_node
                nodes.append(class_node)

            edges.append({
                "relationName": "HASISSUE",
                "from": {"nodeType": "Class", "propertyName": "fullName", "propertyValue": fqn_class},
                "to": {"nodeType": "Issue", "propertyName": "id", "propertyValue": issue_id},
            })

    return {"nodes": nodes, "edges": edges}


def main():
    parser = argparse.ArgumentParser(
        description="Parse PMD CyclomaticComplexity report and create a graph linking methods/classes to complexity issues."
    )
    parser.add_argument("pmd_report", help="Path to the PMD text report file")
    parser.add_argument("source_dir", help="Root directory of the Java source code (needed to resolve packages)")
    parser.add_argument("-o", "--output", default="pmd_cyclomatic.json", help="Output JSON file (default: pmd_cyclomatic.json)")

    args = parser.parse_args()

    print(f"Parsing PMD report: {args.pmd_report}")
    print(f"Source directory: {args.source_dir}")

    graph = parse_pmd_report(args.pmd_report, args.source_dir)
    result = {
        "probeName": "Cyclomatic",
        "nodes": graph["nodes"],
        "edges": graph["edges"]
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Done – {len(result['nodes'])} nodes, {len(result['edges'])} edges")
    print(f"Output written to: {args.output}")


if __name__ == "__main__":
    main()