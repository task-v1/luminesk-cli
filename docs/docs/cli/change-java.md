# `change-java` & `change-lang` commands

Commands to configure system runtime settings (Java version) and user preferences (language).

---

## Syntax

### Change Java Version
```bash
nesk change-java [tag] [options]
```
- **Alias**: `java`

### Change CLI Language
```bash
nesk change-lang [language_code]
```
- **Alias**: `lang`

---

## Options & Arguments

### Options for `change-java`:
- `-j`, `--java <version|image>`: The Java runtime to assign to the server. You can specify a numeric version (e.g. `17` or `21`) which resolves to `eclipse-temurin:<version>-jre`, or a full Docker Hub image string (e.g., `eclipse-temurin:17-jre`).

### Arguments for `change-lang`:
- `language_code`: The ISO language code (e.g., `en`, `ru`, `uk`, `ja`, `zh`). If you omit the language code, the CLI lists the current and available languages.

---

## Examples

### Change a server's Java version to Java 17
```bash
nesk change-java my-server --java 17
```

### Configure a server to use a custom Java container image
```bash
nesk change-java my-server --java eclipse-temurin:21-jre
```

### View list of supported languages
```bash
nesk change-lang
```

### Set CLI language to Russian
```bash
nesk change-lang ru
```
