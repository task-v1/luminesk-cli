# Memory Limits

To prevent Java virtual machines from running out of control and consuming all host memory, Luminesk enforces memory allocation limits on the Docker container.

---

## Default Limit

If no memory limit is specified during server creation, Luminesk assigns a default limit of **`1g`** (1 Gigabyte).

---

## Setting a Custom Limit

You can set custom memory limits when creating a server using the `--memory` (or `-m`) option:

```bash
nesk create --tag heavy-server --memory 2g
```

### Supported Formats:
Luminesk validates the memory input string against a strict format using the regular expression `^[1-9][0-9]*(?:[bkmg])?$`. Allowed units are:
- `b`: Bytes
- `k`: Kilobytes
- `m`: Megabytes (e.g., `512m`)
- `g`: Gigabytes (e.g., `2g`)

---

## How It Is Enforced

Memory limits are enforced at the containerization layer:
1. **Container Resource Constraints**: The limit is passed directly to the Docker engine via the `--memory` flag during container creation:
   ```bash
   docker run --memory 2g ...
   ```
2. **Cgroup Constraints**: The host OS kernel uses control groups (cgroups) to limit the physical memory consumption of the container process. If the server process exceeds this threshold, the kernel will terminate the process (OOM kill).
:::danger
If a server crashes with exit code `137`, it usually means the JVM heap exceeded the container's memory limit, and Docker terminated the process. Consider increasing the memory limit or tuning the Java garbage collector flags if you encounter this.
:::
