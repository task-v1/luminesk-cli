import { open, readdir } from "node:fs/promises";
import { extname, join } from "node:path";

const roots = ["blog", "docs", "src", "static"];
const blockedExtensions = new Set([".avif", ".heic", ".heif", ".icns", ".jxl"]);
const blockedBrands = new Set([
  "avif",
  "avis",
  "heic",
  "heix",
  "hevc",
  "hevx",
  "heim",
  "heis",
  "mif1",
  "msf1",
]);
const blockedFiles = [];

async function blockedSignature(path) {
  const handle = await open(path, "r");
  try {
    const header = Buffer.alloc(4096);
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
    const ftyp = bytes.indexOf(Buffer.from("ftyp"));
    if (ftyp >= 4) {
      const boxStart = ftyp - 4;
      const boxSize = bytes.readUInt32BE(boxStart);
      const boxEnd = Math.min(bytes.length, boxStart + boxSize);
      const brands = [];
      for (let offset = ftyp + 4; offset + 4 <= boxEnd; offset += 4) {
        if (offset !== ftyp + 8) {
          brands.push(bytes.subarray(offset, offset + 4).toString("ascii"));
        }
      }
      if (brands.some((brand) => blockedBrands.has(brand))) {
        return "HEIF/AVIF";
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
