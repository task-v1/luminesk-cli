import { open, readdir } from "node:fs/promises";
import { extname, join } from "node:path";

const roots = ["blog", "docs", "src", "static"];
const blockedExtensions = new Set([".heic", ".heif", ".icns", ".jxl"]);
const blockedFiles = [];

async function blockedSignature(path) {
  const handle = await open(path, "r");
  try {
    const header = Buffer.alloc(32);
    const { bytesRead } = await handle.read(header, 0, header.length, 0);
    const bytes = header.subarray(0, bytesRead);

    if (bytes.subarray(0, 4).toString("ascii") === "icns") return "ICNS";
    if (bytes[0] === 0xff && bytes[1] === 0x0a) return "JPEG XL";
    if (
      bytes.subarray(0, 12).equals(
        Buffer.from([0, 0, 0, 12, 0x4a, 0x58, 0x4c, 0x20, 0x0d, 0x0a, 0x87, 0x0a]),
      )
    ) {
      return "JPEG XL";
    }
    if (bytes.length >= 12 && bytes.subarray(4, 8).toString("ascii") === "ftyp") {
      const brand = bytes.subarray(8, 12).toString("ascii");
      if (
        new Set(["heic", "heix", "hevc", "hevx", "heim", "heis", "mif1", "msf1"]).has(
          brand,
        )
      ) {
        return "HEIF";
      }
    }
    return null;
  } finally {
    await handle.close();
  }
}

async function inspect(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);

    if (entry.isDirectory()) {
      await inspect(path);
    } else if (entry.isFile()) {
      const extension = extname(entry.name).toLowerCase();
      const signature = await blockedSignature(path);
      if (blockedExtensions.has(extension) || signature !== null) {
        blockedFiles.push(signature === null ? path : `${path} (${signature})`);
      }
    }
  }
}

for (const root of roots) {
  await inspect(root);
}

if (blockedFiles.length > 0) {
  console.error(
    "Unsupported documentation image formats:\n" + blockedFiles.join("\n"),
  );
  process.exitCode = 1;
}
