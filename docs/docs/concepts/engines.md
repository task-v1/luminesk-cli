# Server Engines

Luminesk is specifically designed to manage **Nukkit-family** server engines. This page explains what these engines are, why they are supported, and how Luminesk interacts with them.

---

## What is Nukkit?

Nukkit is a popular open-source server software for Minecraft Bedrock Edition written in Java. Unlike the C++ based official Bedrock Dedicated Server (BDS), Nukkit has a powerful plugin API similar to Bukkit/Spigot/Paper on Java Edition. It allows server administrators to load Java-based plugins (`.jar` files) to add custom features, gameplay modes, and administration tools.

---

## Supported Engines

Luminesk supports multiple variants (forks) of Nukkit, each serving a different purpose:

### 1. Nukkit (Classic)
The original Java server core maintained by CloudburstMC. It is highly stable, lightweight, and suitable for classic gameplay. It mainly targets standard Bedrock mechanics.

### 2. PowerNukkitX (PNX)
An advanced fork of Nukkit that adds comprehensive support for newer Minecraft features, including custom blocks, items, entities, world generators, and modern Java versions. It is ideal for developers who want to push Bedrock customization to its limits.

### 3. Nukkit-MOT
A fork focusing on multi-version compatibility (allowing players on different Bedrock client versions to connect simultaneously) and high vanilla alignment.

### 4. Lumi
An optimized and customizable fork based on Nukkit-MOT, focusing on maximizing performance, thread safety, and custom configuration controls.

---

## Engine Commonalities

Luminesk can manage these diverse engines under a single uniform interface because they all share a set of common behaviors:

- **Executable Format**: They all compile to a single runnable `.jar` file (e.g., `nukkit.jar`, `server.jar`).
- **Standard Stdin/Stdout**: They write logs directly to the console output and accept server commands (like `stop`, `op`, `gamemode`) via standard input (stdin).
- **Configuration Files**: They initialize configuration properties (e.g., ports, world names) via key-value text files, which Luminesk can automatically inspect to resolve port bindings.
