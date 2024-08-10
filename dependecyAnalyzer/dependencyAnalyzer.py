import os
import json
import xmltodict

def extract_dependencies(pom_file_path):
    with open(pom_file_path, 'r') as file:
        pom_xml = file.read()
    pom_dict = xmltodict.parse(pom_xml)
    dependencies = pom_dict['project']['dependencies']['dependency']
    return [
        {
            'groupId': dep['groupId'],
            'artifactId': dep['artifactId'],
            'version': dep.get('version', '')
        } for dep in dependencies
    ]

def analyze_source_code(source_directory):
    class_to_dependencies = {}
    abs_source_directory = os.path.abspath(source_directory)
    for root, _, files in os.walk(source_directory):
        for file in files:
            if file.endswith('.java'):
                file_path = os.path.join(root, file)
                abs_file_path = os.path.abspath(file_path)
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                class_name, package_name, imports = None, None, set()
                for line in lines:
                    line = line.strip()
                    if line.startswith('package '):
                        package_name = line[8:-1]
                    elif line.startswith('import '):
                        imports.add(line[7:-1])
                if package_name:
                    class_name = f"{package_name}.{file[:-5]}"
                if class_name:
                    # Ensure the file path starts with "/"
                    file_path_relative = os.path.relpath(abs_file_path, start=abs_source_directory)
                    file_path_formatted = os.path.join("/", file_path_relative)
                    class_to_dependencies[class_name] = {
                        "imports": imports,
                        "file_path": file_path_formatted
                    }
    return class_to_dependencies

def compare_dependencies(dependencies, class_to_dependencies):
    nodes = []
    edges = []
    
    # Create nodes for libraries
    for dep in dependencies:
        nodes.append({
            "type": "Library",
            "groupId": dep['groupId'],
            "artifactId": dep['artifactId'],
            "version": dep['version'],
            "id": f"{dep['groupId']}:{dep['artifactId']}:{dep['version']}"
        })
    
    # Create nodes for files
    for class_name, data in class_to_dependencies.items():
        nodes.append({
            "type": "File",
            "fullName": class_name,
            "fileName": data["file_path"]
        })
    
    # Create edges for dependencies
    for class_name, data in class_to_dependencies.items():
        file_data = {
            "fileName": data["file_path"],
            "type": "File"
        }
        for dep in dependencies:
            group_id = dep['groupId']
            for imp in data["imports"]:
                if imp.startswith(group_id):
                    edges.append({
                        "relationName": "DEPENDS",
                        "from": {
                            "propertyName": "fileName",
                            "nodeType": "File",
                            "propertyValue": file_data["fileName"]
                        },
                        "to": {
                            "propertyName": "id",
                            "nodeType": "Library",
                            "propertyValue": f"{dep['groupId']}:{dep['artifactId']}:{dep['version']}"
                        }
                    })
                    break
    return {"nodes": nodes, "edges": edges}

def main(pom_file_path, source_directory, output_file_path):
    dependencies = extract_dependencies(pom_file_path)
    class_to_dependencies = analyze_source_code(source_directory)
    result = compare_dependencies(dependencies, class_to_dependencies)

    with open(output_file_path, 'w') as f:
        json.dump(result, f, indent=4)


if __name__ == '__main__':
    pom_file_path = "/Users/minamahdipour/MASc/Implementation/petclinic/spring-petclinic/pom.xml"
    source_directory = "/Users/minamahdipour/MASc/Implementation/petclinic/spring-petclinic"
    output_file_path = '/Users/minamahdipour/MASc/Implementation/dependecyAnalyzer/dependencies.json'

    main(pom_file_path, source_directory, output_file_path)
