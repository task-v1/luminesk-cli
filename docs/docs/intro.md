---
sidebar_position: 1
---

# Introduction to Luminesk

**Luminesk** (Nukkit Engine Servers Kit) is a lightweight, efficient command-line interface (CLI) tool designed for managing and orchestrating Minecraft Bedrock Edition servers running on **Nukkit-family** engines.

Whether you are developing plugins locally, running a private server for your friends, or setting up a small production deployment, Luminesk streamlines the entire lifecycle of your server environment.

---

## What is a Nukkit-Family Engine?

Minecraft Bedrock Edition servers traditionally run on the official Bedrock Dedicated Server (BDS) software. However, BDS has limited support for programming APIs and plugins. **Nukkit** is a high-performance Minecraft Bedrock server software written in Java, featuring a robust, developer-friendly plugin API.

Luminesk fully supports and automates the management of the following Nukkit-based engines:
- **Nukkit**: The classic Nukkit server software.
- **PowerNukkitX**: An advanced, feature-rich fork with support for newer Bedrock blocks, entities, and modern Java features.
- **Nukkit-MOT**: A vanilla-focused core with multi-version Bedrock compatibility.
- **Lumi**: A highly optimized and customizable Nukkit-MOT fork.

---

## Why Luminesk?

Managing Minecraft servers manually requires downloading the correct Java runtimes, configuring ports, setting up loops to restart crashed instances, tracking dependencies, and configuring container networks. Luminesk wraps all these operational tasks into a single, intuitive command-line utility.

### Key Features

- ⚡ **Instant Server Provisioning**: Create fully configured server environments in seconds using interactive wizards or command arguments.
- 🐳 **Docker-Powered Isolation**: Run servers safely using isolated Docker containers without polluting your host system with multiple Java versions or dependencies.
- 🔄 **Auto-Restart Loop**: Keep servers online continuously with built-in loop modes that automatically restart the container if the server stops or crashes.
- 📦 **Automated Core Engines Management**: List, download, switch, and upgrade server engines directly from the CLI without manual web downloads.
- 📊 **Unified Server List**: View status, CPU runtime processes, memory limits, ports, and uptime details across all registered servers in a single terminal table.
- 🛠️ **Seamless Environment Diagnostics**: Check repository connections and host configuration issues with built-in diagnostics.

---

## For Whom is Luminesk Intended?

- **Minecraft Bedrock Developers**: Quickly spin up multiple local server configurations with different engines (e.g., Nukkit, PowerNukkitX) and Java runtimes to test plugins.
- **Server Administrators**: Manage small-to-medium server fleets with simple CLI commands like `nesk start`, `nesk stop`, and `nesk list`.
- **Hobbyists & Gamers**: Easily run local Bedrock servers with low resource usage and automated setup.
