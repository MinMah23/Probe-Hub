import json
import re
import os


def read_source_code(file_path):
    """Reads the source code file and returns the lines."""
    with open(file_path, 'r') as file:
        return file.readlines()


def extract_methods_from_source(lines):
    """Extracts methods from the source code."""
    methods = []
    method_pattern = re.compile(
        r'\b(?:public|protected|private|static|final|abstract)?\s+[\w<>\[\]]+\s+(\w+)\s*\(')
    method_start = None
    method_name = None

    for i, line in enumerate(lines):
        method_match = method_pattern.search(line)
        if method_match:
            if method_name:
                methods.append(
                    {'name': method_name, 'start': method_start, 'end': i})
            method_name = method_match.group(1)
            method_start = i
    if method_name:
        methods.append(
            {'name': method_name, 'start': method_start, 'end': len(lines)})

    return methods


def find_method_for_issue(methods, line_number):
    """Finds the method for the given line number, or returns None if not found."""
    for method in methods:
        if method['start'] <= line_number < method['end']:
            return method['name']
    return None


def parse_pmd_report(pmd_report_path, source_code_dir):
    """Parses the PMD report and generates results."""
    nodes = []
    edges = []
    class_nodes = {}
    method_nodes = {}

    with open(pmd_report_path, 'r') as file:
        for line in file:
            match = re.match(
                r'^(\./)?(?P<file>[\S]+):(?P<line>\d+):\s+(?P<rule>\w+):\s+(?P<message>.+)$', line)
            if match:
                file_path = match.group('file')
                line_number = int(match.group('line'))
                rule = match.group('rule')
                message = match.group('message').strip()
                description = message

                issue_id = f"{file_path}:{line_number}:{rule}:{message}"

                print(f"Processing issue: {description}")

                # Determine the absolute path of the source file
                abs_file_path = os.path.join(source_code_dir, file_path)
                if not os.path.exists(abs_file_path):
                    print(f"Source file not found: {abs_file_path}")
                    continue

                lines = read_source_code(abs_file_path)
                methods = extract_methods_from_source(lines)
                method_name = find_method_for_issue(
                    methods, line_number - 1)  # Adjust for 0-based index

                # Extract class and package name from file path
                package_path, class_name = os.path.split(file_path)
                package_name = package_path.replace(
                    '/', '.').replace('\\', '.').strip('.')

                if method_name:
                    method_full_name = f"{package_name}.{
                        class_name}.{method_name}"
                    if method_full_name not in method_nodes:
                        method_nodes[method_full_name] = {
                            "type": "Method",
                            "fullName": method_full_name
                        }
                        nodes.append(method_nodes[method_full_name])

                    edge = {
                        "relationName": "HASISSUE",
                        "from": {
                            "propertyName": "fullName",
                            "nodeType": "Method",
                            "propertyValue": method_full_name
                        },
                        "to": {
                            "propertyName": "id",
                            "nodeType": "Issue",
                            "propertyValue": issue_id
                        }
                    }
                else:
                    class_full_name = f"{package_name}.{class_name}"
                    if class_full_name not in class_nodes:
                        class_nodes[class_full_name] = {
                            "shortName": class_name,
                            "fullName": class_full_name,
                            "type": "Class"
                        }
                        nodes.append(class_nodes[class_full_name])

                    edge = {
                        "relationName": "HASISSUE",
                        "from": {
                            "propertyName": "fullName",
                            "nodeType": "Class",
                            "propertyValue": class_full_name
                        },
                        "to": {
                            "propertyName": "id",
                            "nodeType": "Issue",
                            "propertyValue": issue_id
                        }
                    }
                edges.append(edge)

                # Add issue node
                issue_node = {
                    "id": issue_id,
                    "type": "Issue",
                    "description": description
                }
                nodes.append(issue_node)

    return {"nodes": nodes, "edges": edges}


def write_json(results, output_file_path):
    """Writes the results to a JSON file."""
    with open(output_file_path, 'w') as file:
        json.dump(results, file, indent=4)


def main(pmd_report_path, source_code_dir, output_file_path):
    """Main function to parse the PMD report and generate the JSON file."""
    results = parse_pmd_report(pmd_report_path, source_code_dir)
    write_json(results, output_file_path)


if __name__ == '__main__':
    # Replace with your PMD report path
    pmd_report_path = '/Users/minamahdipour/MASc/Implementation/complexityAnalysis/pmd-report.txt'
    # Replace with the directory containing the source code
    source_code_dir = '/Users/minamahdipour/MASc/Implementation/petclinic/spring-petclinic/'
    # Replace with your desired output path
    output_file_path = '/Users/minamahdipour/MASc/Implementation/complexityAnalysis/results.json'

    main(pmd_report_path, source_code_dir, output_file_path)
