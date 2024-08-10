import subprocess
import javalang
import os
import json
from datetime import datetime


def read_java_source_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()


def get_file_package(code_tree):
    for _, node in code_tree.filter(javalang.tree.PackageDeclaration):
        return node.name


def is_primitive_type(type_name):
    primitive_types = {"boolean", "byte", "char",
                       "short", "int", "long",
                       "float", "double"}
    return type_name in primitive_types


def is_wrapper_class(type_name):
    wrapper_classes = {"Boolean", "Byte", "Character",
                       "Short", "Integer", "Long",
                       "Float", "Double", "ClassLoader",
                       "Object", "Class", "String"}
    return type_name in wrapper_classes


def get_full_method(class_name, package_name, method_name, parameters, import_statements):
    parameter_string = ''
    is_import_found = False

    for type, name in parameters:
        parameter_string += '' if parameter_string == '' else ','
        for import_name in import_statements:
            if import_name.endswith(type):
                parameter_string += f'{import_name}'
                is_import_found = True
                break

        if not is_import_found and (not is_primitive_type(type) and not is_wrapper_class(type)):
            parameter_string += f"{package_name if package_name else ''}.{type}"
        elif not is_import_found and (is_primitive_type(type) or is_wrapper_class(type)):
            parameter_string += type if is_primitive_type(
                type) else f'java.lang.{type}'
        is_import_found = False

    full_method = ''
    if package_name:
        full_method += package_name + '.'
    if class_name:
        full_method += class_name + '.'

    full_method += f'{method_name}({parameter_string})'
    return full_method


def parse_java_file(file_path):
    """Parsing the java file and finding the methods and their line ranges."""

    content = read_java_source_file(file_path)
    tree = javalang.parse.parse(content)
    package_name = get_file_package(tree)
    import_statements = [node.path for _,
                         node in tree.filter(javalang.tree.Import)]

    methods = {}

    for _, class_node in tree.filter(javalang.tree.ClassDeclaration):
        for member in class_node.body:
            if isinstance(member, javalang.tree.MethodDeclaration) and member.position \
                    and member.body and member.name:

                start_line = member.position.line
                end_line = member.body[-1].position.line
                method_parameters = []

                for param in member.parameters:
                    param_name = param.name
                    param_type = param.type.name
                    method_parameters.append((param_type, param_name))
                full_method_name = get_full_method(class_node.name, package_name, member.name,
                                                   method_parameters, import_statements)
                methods[member.name] = (start_line, end_line, class_node.name, package_name,
                                        method_parameters, full_method_name)
    print(f"Parsed methods for {file_path}: {methods}")
    return methods


def get_commit_stats(file_path, start_line, end_line):
    """Get commit statistics for a method"""

    cmd = ['git', 'log', '--oneline', '--follow', '--', file_path]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Failed to get commit stats for {file_path}: {result.stderr}")
        return None, None

    commit_lines = result.stdout.splitlines()
    num_changes = len(commit_lines)

    num_fixes = sum(1 for line in commit_lines if any(
        keyword in line.lower() for keyword in ["issue", "bug", "fix"]))

    return num_changes, num_fixes


def analyze_methods(file_path):

    methods = parse_java_file(file_path)
    methods_data = []

    for method_name, (start_line, end_line, class_name, package_name, method_parameters,
                      full_method_name) in methods.items():
        if method_name:
            num_changes, num_fixes = get_commit_stats(
                file_path, start_line, end_line)
            if num_changes is not None and num_fixes is not None:
                method_info = {
                    "method_name": full_method_name,
                    "num_changes": num_changes,
                    "num_fixes": num_fixes,
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                methods_data.append(method_info)
                print(f"Analyzed method {method_name}: {method_info}")
    return methods_data


def transform_graph_data(methods_data):
    method_nodes = []
    change_log_nodes = []
    contribution_edges = []

    for method in methods_data:
        method_name = method["method_name"]
        num_changes = method["num_changes"]
        num_fixes = method["num_fixes"]
        change_log_id = f"{method_name}_{method['timestamp']}"

        method_nodes.append({"type": "Method", "fullName": method_name})
        change_log_nodes.append({
            "type": "changeLog",
            "numOfChanges": num_changes,
            "numOfFixes": num_fixes,
            "id": change_log_id
        })

        contribution_edges.append({
            "relationName": "HASCHANGELOG",
            "from": {
                "propertyName": "fullName",
                "nodeType": "Method",
                "propertyValue": method_name
            },
            "to": {
                "propertyName": "id",
                "nodeType": "changeLog",
                "propertyValue": change_log_id
            }
        })

    res = {
        "nodes": method_nodes + change_log_nodes,
        "edges": contribution_edges
    }

    print(f"Transformed graph data: {res}")
    return res


def dict_to_json_file(output_folder, dictionary):
    with open(f"{output_folder}/change-tracking.json", 'w') as file:
        json.dump(dictionary, file, indent=2, ensure_ascii=False)
    print(f"Written output to {output_folder}/change-tracking.json")


if __name__ == '__main__':
    input_directory = "/Users/minamahdipour/MASc/Implementation/petclinic/spring-petclinic/src"
    output_folder = "/Users/minamahdipour/MASc/Implementation/frequentChange"
    original_directory = os.getcwd()
    os.chdir(input_directory)
    dir_path = "./main"

    res = []
    for (dirpath, dirnames, filenames) in os.walk(dir_path):
        print(f"Walking directory: {dirpath}")
        for filename in filenames:
            print(f"Found file: {filename}")
            res.append(os.path.join(dirpath, filename))

    print(f"Found Java files: {res}")

    methods_data = []
    for fileName in res:
        if fileName.endswith('.java'):
            methods_data.extend(analyze_methods(fileName))

    graph_data = transform_graph_data(methods_data)

    os.chdir(original_directory)
    dict_to_json_file(output_folder, graph_data)
