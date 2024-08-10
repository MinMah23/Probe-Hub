import json
import os
import sys
import xml.etree.ElementTree as ET
import pandas as pd
from collections import deque
from collections import Counter


# Dynamic Data Analysis Probe

def dda(dynamic_data_file_path, project, projects_file_path):
    def xml_to_csv(file_path):
        tree = ET.parse(file_path)
        root = tree.getroot()

        data = []
        stack = []  # This will keep track of the nodes' depth

        # Iterate over each node using an XPath expression that preserves order
        for node in root.iter():
            # Check if the current node is part of the current path in the stack
            while stack and node not in stack[-1]:
                stack.pop()  # Pop from stack until the current node's parent is at the top of the stack

            # Add the current node to the stack
            stack.append(node)

            # The depth of the current node is its position in the stack minus 1
            depth = len(stack) - 1

            # Collect node details including the calculated depth
            details = {
                'Name': (' ' * depth) + str(node.get('class')) + '.' + str(node.get('methodName')),
            }
            data.append(details)

        # Convert list to DataFrame
        df = pd.DataFrame(data)
        new_file_path = file_path.split('.')[0] + ".csv"
        # Export to CSV
        df.to_csv(new_file_path, index=False)
        return new_file_path

    def transform_name(name):
        leading_spaces = len(name) - len(name.lstrip())
        non_space_chars = name.strip()
        return leading_spaces, non_space_chars


    with open(projects_file_path, 'r') as projects:
        project_found = False
        for data in json.load(projects):
            if data['name'] == project:
                source_basedir = data['source_basedir']
                analysis_results_basedir = data['analysis_results_basedir']
                base_package = data['base_package']
                project_found = True
        if not project_found:
            print('ERROR: project ' + project + ' does not appear in project.json')


    if dynamic_data_file_path.split('.')[1] == 'csv':
        df = pd.read_csv(dynamic_data_file_path, dtype=str)
    elif dynamic_data_file_path.split('.')[1] == 'xml':
        new_file_path = xml_to_csv(dynamic_data_file_path)
        df = pd.read_csv(new_file_path, dtype=str)

    df = df[['Name']]
    df = df[~df['Name'].str.contains("Self time")]
    df = df[df['Name'].str.contains(base_package)]
    df['Transformed'] = df['Name'].apply(transform_name)

    df['Name'] = df['Name'].str.replace(base_package+".", "")
    # Remove the first word before the first '.' (dot) and the parentheses and content at the end
    df['Name'] = df['Name'].str.split('.').str[1:].str.join('.').str.replace(r'\s*\([^()]*\)', '', regex=True)

    # List to store tuples of consecutive rows
    dynamic_calls = []
    dynamic_methods = set()
    dynamic_edges = []
    # Iterate over the DataFrame to find consecutive rows
    for i in range(1, len(df)):
        prev_row = df.iloc[i - 1]
        curr_row = df.iloc[i]
        if prev_row['Name'] == curr_row['Name']:
            continue
        prev_name = prev_row['Name'].split('.')
        curr_name = curr_row['Name'].split('.')
        if curr_row['Transformed'][0] > prev_row['Transformed'][0]:
            dynamic_methods.add(prev_name[-2] + "." + prev_name[-1])
            dynamic_methods.add(curr_name[-2] + "." + curr_name[-1])
            dynamic_edges.append((prev_name[-2] + "." + prev_name[-1],
                                  curr_name[-2] + "." + curr_name[-1]))
            dynamic_calls.append(prev_name[-1]+'(' + prev_name[-2] + ')' + ',DCalls,' + curr_name[-1]+'(' + curr_name[-2] + ')')

    counter = Counter(dynamic_edges)

    # Convert to dictionary if needed
    dynamic_calls_dict = dict(counter)

    nodes = []
    for m in dynamic_methods:
        n = {
            'type': 'Method',
            'name': m.split('.')[1],
            'fullName': m
        }
        nodes.append(n)

    edges = []
    for key, value in dynamic_calls_dict.items():
        e = {
                "from": {
                    "nodeType": "Method",
                    "propertyName": "fullName",
                    "propertyValue": key[0]
                },
                "to": {
                    "nodeType": "Method",
                    "propertyName": "fullName",
                    "propertyValue": key[1]
                },
                "relationName": "DCalls",
                "properties": {
                    "count": value
                }
            }
        edges.append(e)

    json_output = {'nodes': nodes, 'edges': edges}

    # Ensure the directory exists
    os.makedirs(analysis_results_basedir, exist_ok=True)

    with open(analysis_results_basedir + project + '_dda_graph.json', 'w') as json_file:
        json.dump(json_output, json_file, indent=4)
        print(f'Output file was successfully stored in {json_file.name}')

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Incorrect input!")
        print(f"Try \"python {sys.argv[0]} \"projects.json's file path\" \"project's name\" \"dynamic data's file path\"")
        exit()

    dynamic_data_file_path = sys.argv[3]
    project = sys.argv[2]
    projects_file_path = sys.argv[1]

    dda(dynamic_data_file_path, project, projects_file_path)
    # example for running the project for "spring-petclinic" project when the dynamic data is stored in "dynamic_data/Petclinic_forwardcalls_data.csv"
    # python dda_probe.py projects.json spring-petclinic dynamic_data/Petclinic_forwardcalls_data.csv
