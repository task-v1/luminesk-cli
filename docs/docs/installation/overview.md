---
sidebar_position: 1
---

# Installation Overview

This page outlines the requirements and methods available to install **Luminesk**.

---

## System Requirements

Before installing Luminesk, ensure that your system meets the following specifications:

| Requirement | Version | Note |
| :--- | :--- | :--- |
| **Operating System** | Linux, macOS, or Windows | Cross-platform support |
| **Docker** | Latest Version | Required to run and run Minecraft server containers |
| **Python** | **3.13+** | Only required if installing via PyPI or building from source |
:::warning
Luminesk requires Docker to run the Minecraft servers. If Docker is not installed or running, commands like `nesk start` will fail. See the [Troubleshooting: Docker Not Found](../troubleshooting/docker-not-found.md) page if you encounter issues.
:::

---

## Installation Methods

Choose the installation method that best suits your environment and preferences:

### 1. One-Line Installer (Recommended)
The fastest way to install Luminesk. Download and set up the binary for your platform with a single shell command.
* **Go to**: [One-Line Installer](one-line-installer.md)

### 2. Via PyPI
Ideal if you already have Python installed and want to manage Luminesk as a standard Python package.
* **Go to**: [Installation via PyPI](pypi.md)

### 3. Prebuilt Binaries
Download a standalone executable directly from the GitHub releases page. Does not require Python on the host system.
* **Go to**: [Prebuilt Binaries](binaries.md)

### 4. From Source
Best for developers who want to modify Luminesk or contribute to the project.
* **Go to**: [Installation from Source](source.md)
