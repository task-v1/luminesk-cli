# Java Runtimes & Docker Images

Minecraft Bedrock Java engines require matching Java runtimes to execute correctly. Luminesk gives you fine-grained control over which Java environment to boot.

---

## Default Java Version

By default, servers are launched using **Java 21** via the official Eclipse Temurin JRE container image:
- **Default Image**: `eclipse-temurin:21-jre`

---

## Configuring Java Versions

You can customize the Java version at server creation using the `--java` (or `-j`) option:

```bash
nesk create -t test-server --java 17
```

### Supported Inputs:

1. **Short Version Numbers**:
   If you pass a simple integer (e.g. `17` or `21`), Luminesk resolves it to the official `eclipse-temurin` runtime image:
   - `17`  ===>  `eclipse-temurin:17-jre`
   - `21`  ===>  `eclipse-temurin:21-jre`

2. **Custom Docker Images**:
   If you need a specific JDK version, different vendor, or custom debug tooling, you can pass any valid Docker image name:
   - `eclipse-temurin:21-jdk` (contains development tools)
   - `openjdk:21-slim` (minimal openjdk)
   - `azul/zulu-openjdk:17-jre` (Azul Zulu JVM)

---

## Changing Java for Existing Servers

If you need to change the Java version for a server you already created, use the `change-java` command:

```bash
nesk change-java my-server --java 17
```
:::warning
The server must be **stopped** before you can change its Java runtime. If the container is currently running, the command will fail.
:::
