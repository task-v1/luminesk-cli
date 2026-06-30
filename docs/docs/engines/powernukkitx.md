# PowerNukkitX

**PowerNukkitX** (PNX) is a highly customized, advanced fork of Nukkit. It is designed to support the newest Minecraft Bedrock blocks, items, entities, biomes, and world generation mechanics.

---

## Engine Details

- **Identifier**: `pnx`
- **Provider Type**: `maven`
- **Download Source**: [PowerNukkitX Maven Repository](https://repo.powernukkitx.org/releases)
- **Group ID**: `org.powernukkitx`
- **Artifact ID**: `server`
- **Classifier**: `all`
- **Is Snapshot**: `true`

---

## Configuration

Unlike classic Nukkit, PowerNukkitX uses a YAML file for core configurations and network settings:

- **Config File**: `pnx.yml`
- **Port Mapping Key**: `settings.port` (Default: `19132`)

Luminesk parses this YAML file structure to resolve port bindings on Windows and macOS.

---

## Characteristics

### Advantages:
- **Up-to-Date**: Full support for newer Bedrock blocks, items, components, custom entities, and modern world generation (Nether/End dimensions, custom biomes).
- **Extensible API**: Enhanced API extensions for plugin developers.
- **Modern Java**: Optimized to leverage modern JDK features.

### Known Limitations:
- **Resource Footprint**: Higher CPU and RAM consumption compared to classic Nukkit. It is recommended to configure memory limits to at least `2g` using `nesk create --memory 2g` or `nesk change-java`.
- **Compatibilities**: Older legacy Nukkit plugins may require modifications to run on PNX due to API adjustments.
