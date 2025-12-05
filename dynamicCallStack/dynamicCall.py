#!/usr/bin/env python3
import csv
import json
import argparse
import re


def is_method(name):
    return '(' in name and name.endswith(')')


PRIMITIVE_TYPES = {
    'int', 'boolean', 'long', 'double', 'float', 'short', 'byte', 'char'
}

TYPE_MAPPING = {
    'Integer': 'java.lang.Integer',
    'String': 'java.lang.String',
    'Object': 'java.lang.Object',
    'Boolean': 'java.lang.Boolean',
    'Long': 'java.lang.Long',
    'Double': 'java.lang.Double',
    'Float': 'java.lang.Float',
    'Short': 'java.lang.Short',
    'Byte': 'java.lang.Byte',
    'Character': 'java.lang.Character',
    'List': 'java.util.List',
    'Map': 'java.util.Map',
    'Set': 'java.util.Set',
    'Collection': 'java.util.Collection',
    'Locale': 'java.util.Locale',
    'Errors': 'org.springframework.validation.Errors',
    'Model': 'org.springframework.ui.Model',
    'Page': 'org.springframework.data.domain.Page'
}


def fully_qualify_method(method_name, prefix):
    match = re.match(r'(.+?)\((.*?)\)', method_name)
    if not match:
        return method_name
    method_base = match.group(1)
    params = match.group(2)
    if not params:
        return method_name
    param_list = [param.strip() for param in params.split(',')]
    qualified_params = []
    for param in param_list:
        if not param:
            continue
        if param in PRIMITIVE_TYPES:
            qualified_params.append(param)
        elif '.' in param:
            qualified_params.append(param)
        else:
            if param in TYPE_MAPPING:
                qualified_params.append(TYPE_MAPPING[param])
            else:
                # Try to infer package from the method's class package
                package_match = re.match(r'(.+)\.\w+\.\w+$', method_base)
                if package_match:
                    package = package_match.group(1)
                    qualified_params.append(f"{package}.{param}")
                else:
                    qualified_params.append(param)
    return f"{method_base}({','.join(qualified_params)})"


def main():
    parser = argparse.ArgumentParser(
        description="Convert a hierarchical Java profiler CSV (with indentation) into a dynamic call graph JSON."
    )
    parser.add_argument("input_csv", help="Path to the input profiling CSV file (with indented call tree)")
    parser.add_argument("-o", "--output", default="output.json",
                        help="Output JSON file path (default: output.json)")
    parser.add_argument("--prefix", default="org.springframework.samples.petclinic.",
                        help="Default package prefix for FQN resolution (default: Petclinic prefix)")

    args = parser.parse_args()

    input_file = args.input_csv
    output_file = args.output
    prefix = args.prefix.rstrip('.') + '.'  # ensure clean prefix

    nodes_set = set()
    edges_set = set()

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f, quotechar='"', delimiter=',', skipinitialspace=True)
            next(reader, None)  # Skip header

            stack = []

            for row in reader:
                if len(row) < 1:
                    continue
                name_with_space = row[0]
                # Count leading spaces to determine level
                leading_spaces = len(name_with_space) - len(name_with_space.lstrip(' '))
                level = leading_spaces // 2  # usually 2 spaces per level in profilers
                actual_name = name_with_space.strip()

                if actual_name == "Self time" or not is_method(actual_name):
                    continue

                # Clean up common formatting
                actual_name = actual_name.replace(' (', '(')
                actual_name = fully_qualify_method(actual_name, prefix)

                # Pop stack until parent level
                while stack and stack[-1][0] >= level:
                    stack.pop()

                if stack:
                    parent_level, parent_name_raw = stack[-1]
                    parent_name = parent_name_raw.replace(' (', '(')
                    parent_name = fully_qualify_method(parent_name, prefix)

                    if (is_method(parent_name) and is_method(actual_name) and
                            actual_name.startswith(prefix)):
                        edges_set.add((parent_name, actual_name))
                        nodes_set.add(parent_name)
                        nodes_set.add(actual_name)

                stack.append((level, actual_name))

        # Build final graph
        nodes = [{"fullName": name, "type": "Method"} for name in sorted(nodes_set)]
        edges = [
            {
                "relationName": "DCALL",
                "from": {
                    "nodeType": "Method",
                    "propertyName": "fullName",
                    "propertyValue": from_name
                },
                "to": {
                    "nodeType": "Method",
                    "propertyName": "fullName",
                    "propertyValue": to_name
                }
            }
            for from_name, to_name in sorted(edges_set)
        ]

        output = {
            "probeName": "DynamiCall",
            "nodes": nodes,
            "edges": edges
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=4)
        print(f"Success: Dynamic call graph written to {output_file}")
        print(f"   Methods: {len(nodes)}, Calls: {len(edges)}")

    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
        raise
    except Exception as e:
        print(f"Error processing file: {e}")
        raise


if __name__ == "__main__":
    main()