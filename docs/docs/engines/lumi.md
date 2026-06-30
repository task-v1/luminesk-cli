# Lumi

**Lumi** is a specialized fork of Nukkit-MOT that is highly optimized and heavily focused on customization, performance, and bug fixes.

---

## Engine Details

- **Identifier**: `lumi`
- **Provider Type**: `maven`
- **Download Source**: [Lumi Repo Maven Repository](https://repo.lumi.su/releases/)
- **Group ID**: `com.koshakmine`
- **Artifact ID**: `Lumi`

---

## Configuration

Lumi uses a YAML-formatted settings file:

- **Config File**: `settings.yml`
- **Port Mapping Key**: `general.server-port` (Default: `19132`)

Luminesk parses this hierarchical YAML structure to configure container networking.

---

## Characteristics

### Advantages:
- **Optimization Focus**: Contains numerous performance fixes, multi-threading improvements, and garbage collection optimizations to reduce TPS drops.
- **Customization Options**: Adds extra configuration hooks for server owners.
- **MOT Legacy**: Inherits the multi-version compatibility features of Nukkit-MOT.

### Known Limitations:
- **Stability**: Due to aggressive performance tweaks, certain plugins that rely on internal Nukkit engine quirks might require custom adjustments.
