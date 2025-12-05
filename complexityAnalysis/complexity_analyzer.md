# PMD Cyclomatic Complexity Analyzer → Graph Export

This probe parses a **PMD text report** (specifically the `CyclomaticComplexity` rule) and transforms it into a clean, structured **JSON graph** that connects:

- Java **Classes** or **Methods**  
- → to their **Cyclomatic Complexity Issues** (from PMD)

It automatically extracts the method signature (including parameter types), resolves short type names (like `String`, `List`, `Model`) to **fully qualified names**, and builds a ready-to-import graph for tools like **Neo4j**, **Gephi**, or custom dashboards.

Perfect for:
- Identifying the most complex methods in your codebase
- Visualizing technical debt hotspots
- Prioritizing refactoring targets
- Integrating static analysis into architecture fitness functions

### Features

- Accurate parsing of PMD's default text output format
- Smart **FQN resolution** for method parameters (`String` → `java.lang.String`, `Model` → `org.springframework.ui.Model`, etc.)
- Handles both **method-level** and **class-level** complexity warnings
- Infers correct Java package from file paths (supports `src/main/java` layout and flat structures)
- Outputs standardized JSON graph with `probeName: "Cyclomatic"`

### Input Example (PMD report line)



### How to use
```
python complexity_analyzer.py pmd-report.txt source_project -o complexity-graph.json
```
### Command-line Arguments

| Argument         | Required | Description                                                  | Default               |
|------------------|----------|--------------------------------------------------------------|-----------------------|
| `pmd_report`     | Yes      | Path to the PMD text report file                             | –                     |
| `source_dir`     | Yes      | Root directory of the Java source code (to resolve packages)| –                     |
| `-o, --output`   | No       | Output JSON file path                                        | `pmd_cyclomatic.json` |