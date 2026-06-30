# Nukkit-MOT

**Nukkit-MOT** is a fork of Nukkit focusing on multi-version compatibility and a strong vanilla-aligned gameplay experience.

---

## Engine Details

- **Identifier**: `nukkit-mot`
- **Provider Type**: `jenkins`
- **Download Source**: [MOT Jenkins CI Server](https://motci.cn/job/Nukkit-MOT/job/master)

Luminesk queries this Jenkins job endpoint directly to pull build list JSON feeds and download the compiled JAR file.

---

## Configuration

Nukkit-MOT uses standard configuration structures:

- **Config File**: `server.properties`
- **Port Mapping Key**: `server-port` (Default: `19132`)

---

## Characteristics

### Advantages:
- **Multi-Version Protocol**: Allows clients running different Minecraft Bedrock versions (e.g. 1.20 and 1.21) to connect to the same server simultaneously.
- **Vanilla Emulation**: Improved vanilla Bedrock features implementation compared to classic Nukkit.

### Known Limitations:
- **Build Server Dependency**: The download and upgrade features depend on the availability of the `motci.cn` Jenkins server. If the CI build host goes offline, you can run `nesk diagnostic` to verify its status.
