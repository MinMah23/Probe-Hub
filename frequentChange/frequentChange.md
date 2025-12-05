# Changespot Analyzer for Java Code

A probe that extracts every method from a Java codebase, computes how many times each method has been changed in Git history (using `git log -L`), counts how many of those changes look like bug-fixes, and exports the result as a structured JSON graph suitable for visualisation tools (e.g. Neo4j, Gephi, custom dashboards).

The output models two node types:

- **Method** – a Java method with its fully-qualified name
- **Changespot** – a hotspot of change for that method, containing the total number of revisions and the number of probable bug-fix revisions

## Features

- Parses real Java source files with **javalang** (handles generics, arrays, inner classes, etc.)
- Smart fully-qualified name resolution (primitives → `java.lang` → `java.util` → `java.time` → same package → explicit imports)
- Uses `git log -L` to get exact per-line history for each method body
- Detects likely bug-fix commits by simple keyword matching (`fix`, `bug`, `issue`, `patch`, `resolve`)
- Produces a ready-to-import JSON graph (nodes + edges)
- Pure Python 3 – no Java runtime required

## Requirements

| Package       | Minimum version | Install command                              |
|---------------|-----------------|----------------------------------------------|
| Python        | ≥ 3.8           | –                                            |
| javalang      | any             | `pip install javalang`                       |
| Git           | any recent      | Must be available in `PATH`                  |

That’s it! No Maven, Gradle, or JDK needed.

### Optional (recommended)

```bash
pip install javalang tqdm   # tqdm gives a nice progress bar if you add it
```

##  HOw to use it

```
./frequesntChange.py \
    --src   /path/to/your/project/src/main/java \
    --out   output/changespot_graph.json \
    [--git-root /path/to/git/repo]
```

### Command-line Arguments

| Flag         | Required | Description                                                                                   | Default |
|--------------|----------|------------------------------------------------------------------------------------------------|---------|
| `--src`      | Yes      | Root directory that contains your `*.java` source files (usually `src/main/java`)             | –       |
| `--out`      | Yes      | Path of the JSON file that will be written                                                    | –       |
| `--git-root` | No       | Directory that is the root of the Git repository (where `.git` lives). Useful for monorepos. | `.`     |


### Output Explanation

- Method nodes identify the exact method (FQN includes parameter types).
- Each method gets exactly one Changespot node that aggregates:
    - numOfChanges – total Git revisions that touched the method body
    - numOfFixes   – revisions whose commit message contains fix-related keywords

- The changespot_id contains a timestamp so repeated runs do not collide when you import many runs into the same graph database.