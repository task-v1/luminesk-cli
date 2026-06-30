# Creating Your First Server

This guide walks you through setting up and creating your very first Minecraft Bedrock server using **Luminesk**.

---

## Step 1: Diagnose the Environment

Before creating a server, it is a good practice to run a quick diagnostic check to verify that repository sources are accessible and your local setup is fully functional:

```bash
nesk diagnostic
```

If everything is in order, you will see a success panel:
```text
Repository diagnostics finished. All sources responded successfully.
```

---

## Step 2: Choose a Creation Mode

Luminesk allows you to create servers in two ways: using **CLI arguments** (fast and scriptable) or using the **Interactive Wizard** (guided step-by-step).

### Option A: The Interactive Wizard (Recommended for Beginners)

Simply run the creation command without any options:

```bash
nesk create
```

Luminesk will guide you through the setup by asking a series of questions:
1. **Core**: Choose your server core (defaults to `nukkit`).
2. **Name**: Provide a name for the server.
3. **Tag**: Enter a short, unique tag (e.g., `my-server`) which acts as an identifier for commands like starting/stopping.
4. **Directory**: Define where the server files should be stored.
5. **Java/Docker Image**: Select the Java version or runtime container to run the server.

### Option B: CLI Arguments (Direct Creation)

You can specify all configurations directly in the command. This is useful for scripts or experienced users:

```bash
nesk create -n "My Bedrock Server" -d ./servers/my-server -c nukkit -t my-server
```

#### Explaining the Arguments:
- `-n`, `--name`: The display name of the server (e.g., `"My Bedrock Server"`).
- `-d`, `--dir`: The path where server files will be downloaded and initialized.
- `-c`, `--core`: The engine core identifier (e.g., `nukkit`, `pnx`, `nukkit-mot`, or `lumi`).
- `-t`, `--tag`: A unique, clean alphanumeric tag (e.g., `my-server`).

---

## Step 3: Creation output

Luminesk will resolve the core in the online registry, fetch the latest package version, save it locally to your cache, initialize the server config files in the specified directory, and register the server. 

Once finished, a success box displays the server registry details:

```text
┌─────────────────────────────────────────────────────────────┐
│                      Server created                         │
│                                                             │
│  Name:           My Bedrock Server                          │
│  Tag:            my-server                                  │
│  Core:           Nukkit                                     │
│  Core Version:   1.21.0-r1                                  │
│  JAR:            nukkit-1.21.0-r1.jar                       │
│  Java:           eclipse-temurin:21-jre                     │
│  Memory Limit:   1g                                         │
│  Path:           /home/user/servers/my-server               │
└─────────────────────────────────────────────────────────────┘
```

Your server is now initialized and ready to launch!
