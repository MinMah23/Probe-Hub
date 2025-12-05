package com.probe;

import spoon.Launcher;
import spoon.reflect.CtModel;
import spoon.reflect.code.CtInvocation;
import spoon.reflect.declaration.CtMethod;
import spoon.reflect.declaration.CtType;
import spoon.reflect.declaration.CtExecutable;
import spoon.reflect.visitor.filter.TypeFilter;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

public class SpoonAnalyzer {

    public static void main(String[] args) {
        if (args.length != 2) {
            System.err.println("Usage: java -jar spoon-analyzer.jar <project-directory> <output-json-path>");
            System.err.println("Example: java -jar spoon-analyzer.jar /path/to/my-project /tmp/test-impact-graph.json");
            System.exit(1);
        }

        String projectDir = args[0];
        String outputPath = args[1];

        Path projectPath = Path.of(projectDir).toAbsolutePath().normalize();
        if (!Files.isDirectory(projectPath)) {
            System.err.println("Error: Project directory does not exist or is not a directory: " + projectDir);
            System.exit(1);
        }

        Launcher launcher = new Launcher();
        Path mainSrc = projectPath.resolve("src/main/java");
        Path testSrc = projectPath.resolve("src/test/java");

        if (Files.isDirectory(mainSrc)) {
            launcher.addInputResource(mainSrc.toString());
        } else {
            System.out.println("Warning: src/main/java not found (skipping main sources)");
        }

        if (Files.isDirectory(testSrc)) {
            launcher.addInputResource(testSrc.toString());
        } else {
            System.out.println("Warning: src/test/java not found (no tests will be analyzed)");
        }

        launcher.getEnvironment().setComplianceLevel(17);
        launcher.getEnvironment().setAutoImports(true);

        try {
            launcher.buildModel();
        } catch (Exception e) {
            System.err.println("Failed to build Spoon model. Check that the project has valid Java sources.");
            e.printStackTrace();
            System.exit(1);
        }

        CtModel model = launcher.getModel();

        Set<String> coveredMethods = new HashSet<>();
        Set<String> testMethods = new HashSet<>();
        List<String> nodeJson = new ArrayList<>();
        List<String> edgeJson = new ArrayList<>();

        List<CtMethod<?>> allMethods = model.getElements(new TypeFilter<>(CtMethod.class));

        for (CtMethod<?> method : allMethods) {
            CtType<?> declaringType = method.getDeclaringType();
            if (declaringType == null) continue;

            String fullName = buildFullName(method);

            if (isTestMethod(method, declaringType)) {
                testMethods.add(fullName);
            }

            List<CtInvocation<?>> invocations = method.getElements(new TypeFilter<>(CtInvocation.class));
            for (CtInvocation<?> inv : invocations) {
                if (inv.getExecutable() == null || inv.getExecutable().getDeclaration() == null) continue;

                CtExecutable<?> executable = inv.getExecutable().getDeclaration();
                if (!(executable instanceof CtMethod<?> target)) continue;

                CtType<?> targetType = target.getDeclaringType();
                if (targetType == null) continue;

                if (isFromMainCode(targetType, projectPath)) {
                    String calleeFullName = buildFullName(target);
                    coveredMethods.add(calleeFullName);

                    if (isTestMethod(method, declaringType)) {
                        String edge = "{\"relationName\": \"TESTS\", " +
                                "\"from\": {\"nodeType\": \"TestMethod\", \"propertyName\": \"fullName\", \"propertyValue\": \"" + escapeJson(fullName) + "\"}, " +
                                "\"to\": {\"nodeType\": \"Method\", \"propertyName\": \"fullName\", \"propertyValue\": \"" + escapeJson(calleeFullName) + "\"}}";
                        edgeJson.add(edge);
                    }
                }
            }
        }

        for (CtMethod<?> method : allMethods) {
            CtType<?> declaringType = method.getDeclaringType();
            if (declaringType == null) continue;

            String fullName = buildFullName(method);
            boolean isTest = testMethods.contains(fullName);
            boolean isCovered = coveredMethods.contains(fullName);

            if (isTest || isCovered) {
                String nodeType = isTest ? "TestMethod" : "Method";
                nodeJson.add("{\"fullName\": \"" + escapeJson(fullName) + "\", \"type\": \"" + nodeType + "\"}");
            }
        }

        String jsonOutput = """
            {
                "probeName": "REGTEST",
                "nodes": [
                    %s
                ],
                "edges": [
                    %s
                ]
            }""".formatted(
                String.join(",\n        ", nodeJson).isBlank() ? "" : "        " + String.join(",\n        ", nodeJson),
                String.join(",\n        ", edgeJson).isBlank() ? "" : "        " + String.join(",\n        ", edgeJson)
        );

        try {
            Path outputFile = Path.of(outputPath).toAbsolutePath();
            Files.createDirectories(outputFile.getParent());
            Files.writeString(outputFile, jsonOutput);
            System.out.println("Graph successfully saved to: " + outputFile);
            System.out.println("Nodes: " + nodeJson.size() + " | Edges: " + edgeJson.size());
        } catch (Exception e) {
            System.err.println("Failed to write output file: " + outputPath);
            e.printStackTrace();
            System.exit(1);
        }
    }

    private static boolean isTestMethod(CtMethod<?> method, CtType<?> declaringType) {
        String methodName = method.getSimpleName();
        String className = declaringType.getSimpleName();

        return method.getAnnotations().stream().anyMatch(a -> a.toString().contains("@Test"))
                || methodName.startsWith("test")
                || className.endsWith("Test")
                || className.endsWith("Tests");
    }

    private static boolean isFromMainCode(CtType<?> type, Path projectRoot) {
        var position = type.getPosition();
        if (position == null || position.getFile() == null) return false;
        return position.getFile().toPath().startsWith(projectRoot.resolve("src/main/java"));
    }

    private static String buildFullName(CtMethod<?> method) {
        CtType<?> type = method.getDeclaringType();
        if (type == null) return method.getSimpleName() + "()";

        String qualifiedName = type.getQualifiedName();
        String simpleName = method.getSimpleName();

        StringBuilder params = new StringBuilder("(");
        var parameters = method.getParameters();
        for (int i = 0; i < parameters.size(); i++) {
            if (i > 0) params.append(", ");
            String paramType = parameters.get(i).getType() != null ? parameters.get(i).getType().getQualifiedName() : "java.lang.Object";
            params.append(paramType);
        }
        params.append(")");

        return qualifiedName + "." + simpleName + params.toString();
    }

    private static String escapeJson(String s) {
        return s.replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t");
    }
}