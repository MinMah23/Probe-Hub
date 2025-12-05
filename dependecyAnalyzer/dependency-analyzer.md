# Maven Dependency to Source Analyzer

This probe analyzes a Maven project's `pom.xml` and scans all `.java` source files to build a **real dependency graph** showing which source files actually **import and use** declared libraries.

It answers the critical question:  
> *"Which of my declared dependencies are actually used in code?"*

Perfect for:
- Detecting unused dependencies
- Architecture analysis
- Microservices dependency mapping
- Refactoring & cleanup

## Features

- Parses `pom.xml` using `xmltodict`
- Recursively scans Java source for `import` statements
- Matches imports to Maven `groupId`
- Outputs clean JSON graph (ready for Neo4j, Gephi, etc.)
- No external tools or Java runtime needed

## Requirements

```bash
pip install xmltodict
```

## How to use it
```
python dependency_analyzer.py <pom.xml> <source_directory> [--output output.json]
```

### Command-line Arguments

| Argument           | Required | Description                                                                 | Default             |
|--------------------|----------|-----------------------------------------------------------------------------|---------------------|
| `pom`              | Yes      | Path to the `pom.xml` file                                                  | –                   |
| `source`           | Yes      | Root directory containing `.java` files (usually project root or `src/main/java`) | –                   |
| `-o, --output`     | No       | Output JSON file path                                                       | `dependencies.json` |