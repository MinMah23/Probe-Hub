#TEST - Test Impact Graph Generator (Using Spoon)

**REGTEST** is a lightweight static analysis probe that uses **[Spoon](https://spoon.gforge.inria.fr/)** to analyze a Java project and generate a **test-impact graph** showing exactly which production methods are exercised by which test methods.

The output is a clean JSON file containing:
- All test methods
- All production methods that are directly invoked from tests
- Directed edges from test methods → production methods they call

This graph is perfect for **Test Impact Analysis (TIA)**, smart test selection, CI optimization, or visualization.

Only **actually tested methods** appear in the result (no noise from untested code).

## Output Format

```json
{
  "probeName": "REGTEST",
  "nodes": [ { "fullName": "com.example.Service.doWork()", "type": "Method" } ],
  "edges": [ { "relationName": "TESTS", "from": "...", "to": "..." } ]
}
```
## Requirements

- Java 17+
- Spoon library (include via Maven/Gradle or fat JAR)

### Maven Dependency
```
<dependency>
    <groupId>fr.inria.gforge.spoon</groupId>
    <artifactId>spoon-core</artifactId>
    <version>10.4.2</version>
</dependency>
```

## How to Run

| Argument # | Name                  | Description                                                                                 | Example                              |
|------------|-----------------------|---------------------------------------------------------------------------------------------|--------------------------------------|
| 1          | **project-directory** | Absolute or relative path to the root of the Java project (must contain `src/`)             | `/home/me/my-app` or `../service` or `.` |
| 2          | **output-json-file**  | Full path where the generated `test-impact-graph.json` will be saved                        | `./graph.json` or `/tmp/tia.json`    |

### Option 1: Run directly (with classpath)

```
java -cp "your-jar-with-dependencies.jar" com.probe.SpoonAnalyzer \
  /path/to/your/project \
  /path/to/output/test-impact-graph.json
```

### Option 2: Build a fat JAR (recommended)
Use Maven Assembly Plugin or Shade to create an executable JAR:
```
java -jar regtest-analyzer.jar \
  ./my-awesome-project \
  ./output/test-impact-graph.json
```

  This will:

- Scan src/main/java and src/test/java
- Detect JUnit tests
- Trace method calls from tests → production code
- Save result to tia-graph.json