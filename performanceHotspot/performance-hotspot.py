import csv
import json
import re
import sys
import os
from datetime import datetime
from pathlib import Path


def is_primitive_type(type_name):
    return type_name in {"boolean", "byte", "char", "short", "int", "long", "float", "double"}


def is_wrapper_class(type_name):
    return type_name in {
        "Boolean", "Byte", "Character", "Short", "Integer", "Long",
        "Float", "Double", "String", "Object", "Class", "ClassLoader"
    }


def transform_method_signature(method_signature):
    """Convert YourKit-style method name to clean full signature."""
    if '(' not in method_signature:
        return None

    method_name, params_part = method_signature.split('(', 1)
    params = [p.strip()
              for p in params_part.rstrip(')').split(',') if p.strip()]

    # Common fixes for Spring / Java types
    replacements = {
        "Locale": "java.util.Locale",
        "BindingResult": "org.springframework.validation.BindingResult",
        "Model": "org.springframework.ui.Model",
        "RedirectAttributes": "org.springframework.web.servlet.mvc.support.RedirectAttributes",
        "HttpServletRequest": "javax.servlet.http.HttpServletRequest",
        "HttpServletResponse": "javax.servlet.http.HttpServletResponse",
    }

    converted = []
    for p in params:
        if p in replacements:
            converted.append(replacements[p])
        elif is_primitive_type(p):
            converted.append(p)
        elif is_wrapper_class(p):
            converted.append(f"java.lang.{p}")
        else:
            converted.append(p)

    return f"{method_name.strip()}".replace("()", f"({','.join(converted)})")


def extract_number(value):
    match = re.search(r"([0-9.]+)", value.replace(",", ""))
    return float(match.group(1)) if match else 0.0


def extract_integer(value):
    match = re.search(r"([0-9]+)", value.replace(",", ""))
    return int(match.group(1)) if match else 0


def parse_performance_csv(csv_path):
    data = []
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["Name"].strip()
            if not name.startswith("org.springframework.samples.petclinic"):
                continue

            sig = transform_method_signature(name)
            if not sig:
                continue

            data.append({
                "method_name": sig.replace(" ", ""),
                "self_time": extract_number(row.get("Self Time", "0")),
                "self_time_cpu": extract_number(row.get("Self Time (CPU)", "0")),
                "total_time": extract_number(row.get("Total Time", "0")),
                "total_time_cpu": extract_number(row.get("Total Time (CPU)", "0")),
                "invocations": extract_integer(row.get("Invocations", "0")),
                "timestamp": timestamp
            })
    return data


def parse_memory_csv(csv_path):
    data = {}
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["Name"].strip()
            if not name.startswith("org.springframework.samples.petclinic"):
                continue

            sig = transform_method_signature(name)
            if not sig:
                continue

            data[sig] = {
                "live_bytes": extract_number(row.get("Live Bytes", "0")),
                "allocated_objects": extract_integer(row.get("Allocated Objects", "0"))
            }
    return data


def build_graph(perf_data, mem_data):
    method_nodes = []
    hotspot_nodes = []
    edges = []

    for item in perf_data:
        method = item["method_name"]
        hotspot_id = f"{method}_{item['timestamp']}"

        hotspot = {
            "type": "PerformanceHotspot",
            "id": hotspot_id,
            "self_time": item["self_time"],
            "self_time_cpu": item["self_time_cpu"],
            "total_time": item["total_time"],
            "total_time_cpu": item["total_time_cpu"],
            "invocations": item["invocations"],
        }

        if method in mem_data:
            mem = mem_data[method]
            hotspot["live_bytes"] = mem["live_bytes"]
            hotspot["allocated_objects"] = mem["allocated_objects"]

        hotspot_nodes.append(hotspot)

        method_nodes.append({
            "type": "Method",
            "fullName": method
        })

        edges.append({
            "relationName": "HASPERFORMANCE",
            "from": {"nodeType": "Method", "propertyName": "fullName", "propertyValue": method},
            "to": {"nodeType": "PerformanceHotspot", "propertyName": "id", "propertyValue": hotspot_id}
        })

    return {
        "probeName": "HotSpot",
        "nodes": method_nodes + hotspot_nodes,
        "edges": edges
    }


def main():
    if len(sys.argv) != 4:
        print("ERROR: Exactly 3 arguments required.\n")
        print("Usage:")
        print(
            "  python hotspot_analyzer.py <performance.csv> <memory.csv> <output-directory>")
        print("\nExample:")
        print("  python hotspot_analyzer.py perf.csv memory.csv ./results")
        sys.exit(1)

    perf_csv = sys.argv[1]
    mem_csv = sys.argv[2]
    out_dir = Path(sys.argv[3])

    for p in [perf_csv, mem_csv]:
        if not Path(p).is_file():
            print(f"ERROR: File not found: {p}")
            sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)

    print("Parsing performance data...")
    perf_data = parse_performance_csv(perf_csv)

    print("Parsing memory data...")
    mem_data = parse_memory_csv(mem_csv)

    print("Building graph...")
    graph = build_graph(perf_data, mem_data)

    output_file = out_dir / "performance-tracking2.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2)

    print(
        f"Success! Generated {len(graph['nodes'])} nodes and {len(graph['edges'])} edges")
    print(f"Output saved to: {output_file.resolve()}")


if __name__ == "__main__":
    main()
