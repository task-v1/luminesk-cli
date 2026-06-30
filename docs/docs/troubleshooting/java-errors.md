# Troubleshooting: Java & Image Pull Errors

If Luminesk fails to locate a Java runtime version or cannot pull the required container image from Docker Hub, it will throw an error.

---

## Error Messages

### 1. Invalid Java Runtime Format
```text
Error: Invalid Java runtime 'java21'. Use a version like 21 or a Docker image like eclipse-temurin:21-jre.
```

- **Cause**: The value passed to `--java` contains invalid letters, spaces, or decimal points.
- **Solution**: 
  - Use simple integers: `17` or `21` (resolves to `eclipse-temurin:<version>-jre`).
  - Use a full image identifier: `eclipse-temurin:21-jre`.

---

### 2. Docker Pull Failure
```text
Error: Docker failed to pull Java runtime image 'eclipse-temurin:21-jre': Error response from daemon...
```

- **Cause**: Docker cannot download the image. Common causes include:
  - No internet connection.
  - Docker Hub rate limits.
  - DNS resolution failures.
  - Docker daemon is configured to work in offline mode.
- **Solution**:
  - Verify your internet connectivity by running `docker pull eclipse-temurin:21-jre` manually in your terminal.
  - Configure a Docker registry mirror if you reside in a region with restricted access to Docker Hub.

---

## Changing Java Version

If a server is crashing because it was initialized with an incompatible Java version (e.g. trying to run PowerNukkitX on Java 8), stop the server and change the runtime:

```bash
nesk change-java my-server --java 21
```
