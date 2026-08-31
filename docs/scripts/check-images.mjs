import { readdir } from "node:fs/promises";
import { extname, join } from "node:path";

const roots = ["blog", "docs", "src", "static"];
const blockedExtensions = new Set([".heic", ".heif", ".icns", ".jxl"]);
const blockedFiles = [];

async function inspect(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);

    if (entry.isDirectory()) {
      await inspect(path);
    } else if (
      entry.isFile() &&
      blockedExtensions.has(extname(entry.name).toLowerCase())
    ) {
      blockedFiles.push(path);
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
