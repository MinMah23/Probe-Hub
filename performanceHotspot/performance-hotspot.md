# HotSpot Analyzer – Performance & Memory Hotspot Graph Generator

This probe converts **CPU/Memmory CSV snapshots** (CPU/Memory profiling) from the project into a clean, structured JSON graph suitable for:

- Performance dashboards
- Hotspot visualization tools
- Integration with test impact or monitoring systems

The output follows a node/edge model compatible with tools that expect `probeName`, `nodes`, and `edges`.

---

### Output Example (`performance-tracking2.json`)

```json
{
  "probeName": "HotSpot",
  "nodes": [
    { "type": "Method", "fullName": "org.springframework.samples.petclinic.owner.OwnerController.processFindForm()" },
    { "type": "PerformanceHotspot", "id": "..._20250405123045", "self_time": 125.4, ... }
  ],
  "edges": [
    {
      "relationName": "HASPERFORMANCE",
      "from": { "nodeType": "Method", "propertyName": "fullName", "propertyValue": "..." },
      "to": { "nodeType": "PerformanceHotspot", "propertyName": "id", "propertyValue": "..." }
    }
  ]
}
```

## Requirements

Python 3.8+

## How to use it
```
python performance_analyzer.py <performance-csv> <memory-csv> <output-directory>
```
| Argument # | Name               | Description                                              | Example                          |
|------------|--------------------|----------------------------------------------------------|----------------------------------|
| 1          | performance-csv    | Path to YourKit CPU/Time profiling CSV                   | `prof-time.csv`                  |
| 2          | memory-csv         | Path to YourKit Memory profiling CSV                     | `prof-memory.csv`                |
| 3          | output-directory   | Folder where `performance-tracking2.json` will be saved  | `./results` or `/tmp/hotspots`   |