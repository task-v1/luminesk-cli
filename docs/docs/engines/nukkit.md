# Nukkit (Classic)

**Nukkit** is the original, classic Java-based server software for Minecraft Bedrock Edition. It forms the base of all other engines supported by Luminesk.

---

## Engine Details

- **Identifier**: `nukkit`
- **Provider Type**: `maven`
- **Download Source**: [OpenCollab Maven Repository](https://repo.opencollab.dev/maven-snapshots)
- **Group ID**: `cn.nukkit`
- **Artifact ID**: `nukkit`
- **Is Snapshot**: `true`

---

## Configuration

Nukkit stores all primary settings in a single flat file:

- **Config File**: `server.properties`
- **Port Mapping Key**: `server-port` (Default Bedrock Port: `19132`)

Luminesk reads this property value to bind the correct container port when running on non-Linux hosts.

---

## Characteristics

### Advantages:
- **High Stability**: Built on a mature codebase with years of community testing.
- **Resource Efficiency**: Extremely low RAM and CPU footprint compared to heavier forks.
- **Simple API**: Ideal for basic plugins and standard Bedrock server setups.

### Known Limitations:
- **Feature Gap**: Limited built-in support for newer Bedrock blocks, items, custom entities, and complex world generation features. For modern Minecraft Bedrock features, it is recommended to use **PowerNukkitX**.
