import csv
import json
import re
from datetime import datetime


def is_primitive_type(type_name):
    primitive_types = {"boolean", "byte", "char",
                       "short", "int", "long", "float", "double"}
    return type_name in primitive_types


def is_wrapper_class(type_name):
    wrapper_classes = {"Boolean", "Byte", "Character", "Short", "Integer",
                       "Long", "Float", "Double", "ClassLoader", "Object", "Class", "String"}
    return type_name in wrapper_classes


def transform_method_signature(method_signature):
    if '(' in method_signature:
        method_name, params = method_signature.split('(')
        params = params.rstrip(')').split(',')

        def convert_param(param):
            param = param.strip()
            if is_primitive_type(param):
                return param
            if is_wrapper_class(param):
                return f"java.lang.{param}"
            return param

        converted_params = [convert_param(param) for param in params if param]
        return f"{method_name.strip()}({','.join(converted_params)})"
    else:
        return None


def extract_number(value):
    number_pattern = re.compile(r"([0-9.]+)")
    match = number_pattern.search(value)
    return float(match.group(1)) if match else 0.0


def extract_integer(value):
    number_pattern = re.compile(r"([0-9]+)")
    match = number_pattern.search(value)
    return int(match.group(1)) if match else 0


def parse_performance_csv(csv_file_path):
    performance_data = []
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    with open(csv_file_path, mode='r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            method_name = row["Name"].strip()
            if method_name.startswith("org.springframework.samples.petclinic"):
                method_name = transform_method_signature(method_name)
                if method_name:
                    performance_info = {
                        "method_name": method_name.replace(" ", ""),
                        "self_time": extract_number(row["Self Time"].strip()),
                        "self_time_cpu": extract_number(row["Self Time (CPU)"].strip()),
                        "total_time": extract_number(row["Total Time"].strip()),
                        "total_time_cpu": extract_number(row["Total Time (CPU)"].strip()),
                        "invocations": int(row["Invocations"].strip().replace(',', '')),
                        "timestamp": timestamp
                    }
                    performance_data.append(performance_info)
    return performance_data


def parse_memory_csv(csv_file_path):
    memory_data = {}

    with open(csv_file_path, mode='r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            method_name = row["Name"].strip()
            if method_name.startswith("org.springframework.samples.petclinic"):
                method_name = transform_method_signature(method_name)
                if method_name:
                    memory_info = {
                        "live_bytes": extract_number(row["Live Bytes"].strip()),
                        "allocated_objects": extract_integer(row["Allocated Objects"].strip())
                    }
                    memory_data[method_name.replace(" ", "")] = memory_info
    return memory_data


def transform_graph_data(performance_data, memory_data):
    method_nodes = []
    performance_nodes = []
    method_performance_edges = []

    for performance in performance_data:
        performance_hotspot_id = f"{performance['method_name']}_{
            performance['timestamp']}"

        # Create a node for the performance hotspot
        performance_node = {
            "type": "PerformanceHotspot",
            "id": performance_hotspot_id,
            "self_time": performance["self_time"],
            "self_time_cpu": performance["self_time_cpu"],
            "total_time": performance["total_time"],
            "total_time_cpu": performance["total_time_cpu"],
            "invocations": performance["invocations"]
        }

        # Add memory data if available
        if performance["method_name"] in memory_data:
            memory_info = memory_data[performance["method_name"]]
            performance_node["live_bytes"] = memory_info["live_bytes"]
            performance_node["allocated_objects"] = memory_info["allocated_objects"]

        performance_nodes.append(performance_node)

        # Create a node for the method
        method_nodes.append({
            "type": "Method",
            "fullName": performance["method_name"]
        })

        # Create an edge between the method and performance hotspot
        method_performance_edges.append({
            "relationName": "HASPERFORMANCE",
            "from": {
                "propertyName": "fullName",
                "nodeType": "Method",
                "propertyValue": performance["method_name"]
            },
            "to": {
                "propertyName": "id",
                "nodeType": "PerformanceHotspot",
                "propertyValue": performance_hotspot_id
            }
        })

    res = {
        "nodes": method_nodes + performance_nodes,
        "edges": method_performance_edges
    }

    print(f"Transformed graph data: {res}")
    return res


def dict_to_json_file(output_folder, dictionary):
    with open(f"{output_folder}/performance-tracking.json", 'w', encoding='utf-8') as file:
        json.dump(dictionary, file, indent=2, ensure_ascii=False)
    print(f"Written output to {output_folder}/performance-tracking.json")


if __name__ == '__main__':
    performance_csv = "/Users/minamahdipour/MASc/Implementation/performanceHotspot/VisualVM-res/hotspot.csv"
    memory_csv = "/Users/minamahdipour/MASc/Implementation/performanceHotspot/VisualVM-res/memory-res.csv"
    output_folder = "/Users/minamahdipour/MASc/Implementation/performanceHotspot/"

    performance_data = parse_performance_csv(performance_csv)
    memory_data = parse_memory_csv(memory_csv)
    graph_data = transform_graph_data(performance_data, memory_data)

    dict_to_json_file(output_folder, graph_data)
