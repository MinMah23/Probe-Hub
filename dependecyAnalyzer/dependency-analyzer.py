#!/usr/bin/env python3
import os
import json
import argparse
import xmltodict


def extract_dependencies(pom_file_path):
    with open(pom_file_path, 'r', encoding='utf-8') as file:
        pom_xml = file.read()
    pom_dict = xmltodict.parse(pom_xml)

    deps_node = pom_dict['project'].get('dependencies', {})
    dependencies = deps_node.get('dependency', []) if deps_node else []

    if not isinstance(dependencies, list):
        dependencies = [dependencies]

    return [
        {
            'groupId': dep['groupId'],
            'artifactId': dep['artifactId'],
            'version': dep.get('version', 'UNKNOWN')
        }
        for dep in dependencies
    ]


def analyze_source_code(source_directory):
    class_to_dependencies = {}
    abs_source_directory = os.path.abspath(source_directory)

    for root, _, files in os.walk(source_directory):
        for file in files:
            if file.endswith('.java'):
                file_path = os.path.join(root, file)
                abs_file_path = os.path.abspath(file_path)

                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                package_name = None
                imports = set()

                for line in lines:
                    line = line.strip()
                    if line.startswith('package '):
                        package_name = line[8:-1]
                    elif line.startswith('import '):
                        import_name = line[7:-1]
                        if not import_name.endswith(';'):
                            continue
                        imports.add(import_name[:-1] if import_name.endswith(';') else import_name)

                if package_name:
                    relative = os.path.relpath(abs_file_path, abs_source_directory)
                    file_path_formatted = '/' + relative.replace(os.sep, '/')
                    class_to_dependencies[file_path_formatted] = {"imports": imports}

    return class_to_dependencies


def compare_dependencies(dependencies, class_to_dependencies):
    nodes = []
    edges = []

    # File nodes
    for file_path in class_to_dependencies:
        nodes.append({
            "fileName": file_path,
            "type": "File"
        })

    # Library nodes
    for dep in dependencies:
        uid = f"{dep['groupId']}:{dep['artifactId']}:{dep['version']}"
        nodes.append({
            "type": "Library",
            "groupId": dep['groupId'],
            "artifactId": dep['artifactId'],
            "version": dep['version'],
            "uid": uid
        })

    # Edges: File → Library (if import starts with groupId)
    for file_path, data in class_to_dependencies.items():
        file_imports = data["imports"]
        for dep in dependencies:
            group_id = dep['groupId']
            uid = f"{dep['groupId']}:{dep['artifactId']}:{dep['version']}"

            if any(imp.startswith(group_id) for imp in file_imports):
                edges.append({
                    "relationName": "DEPENDS",
                    "from": {
                        "nodeType": "File",
                        "propertyName": "fileName",
                        "propertyValue": file_path
                    },
                    "to": {
                        "nodeType": "Library",
                        "propertyName": "uid",
                        "propertyValue": uid
                    }
                })

    return {"probeName": "POM", "nodes": nodes, "edges": edges}


def main():
    parser = argparse.ArgumentParser(
        description="Analyze Maven (pom.xml) dependencies and map them to actual imports in Java source code."
    )
    parser.add_argument("pom", help="Path to the pom.xml file")
    parser.add_argument("source", help="Root directory containing Java source files (e.g. src/main/java or project root)")
    parser.add_argument("-o", "--output", default="dependencies.json",
                        help="Output JSON file path (default: dependencies.json)")

    args = parser.parse_args()

    print(f"Reading pom.xml: {args.pom}")
    print(f"Scanning sources: {args.source}")

    dependencies = extract_dependencies(args.pom)
    class_to_deps = analyze_source_code(args.source)
    result = compare_dependencies(dependencies, class_to_deps)

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4)

    print(f"Success! Graph saved to {args.output}")
    print(f"   Files: {len(class_to_deps)} | Libraries: {len(dependencies)} | Dependencies: {len(result['edges'])}")


if __name__ == '__main__':
    main()