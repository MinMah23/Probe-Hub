# Dynamic Call Graph Extractor (from Profiling CSV)

This probe converts a **hierarchical profiling CSV** (typically exported from tools like VisualVM, YourKit, JProfiler, or IntelliJ Profiler) into a clean **dynamic call graph** in JSON format — ready to be imported into graph databases (Neo4j, Gephi) or visualization tools.

It extracts real method call relationships observed at runtime and resolves short type names (like `String`, `List`, `Integer`) into fully qualified class names using smart heuristics and a predefined mapping.

Perfect for analyzing actual execution paths in Spring Boot / Java applications (example tuned for **Spring Petclinic**).

## Input Example (CSV format)

Your input CSV should look like this (common in many Java profilers):

```csv
"  methodName(param1, param2)", Time, Self Time, Invocations
"PetClinicController.showOwner(Owner)", 1250, 320, 42
"  OwnerService.findOwnerById(int)", 890, 110, 42
"    OwnerRepository.findById(Integer)", 720, 720, 42
```

## How to use it
```
python dynamicCall.py profiling_data.csv --output project_calls.json
```

### Command-line Arguments

| Argument            | Required | Description                                      | Default       |
|---------------------|----------|--------------------------------------------------|---------------|
| `input_csv_file`    | Yes      | Path to the profiling CSV file (with indented call tree) | –             |
| `output_json_file`  | No       | Output JSON file path                            | `output.json` |