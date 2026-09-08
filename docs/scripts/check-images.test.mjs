import assert from "node:assert/strict";
import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import test from "node:test";

const script = join(dirname(fileURLToPath(import.meta.url)), "check-images.mjs");

async function fixture(files) {
  const root = await mkdtemp(join(tmpdir(), "luminesk-images-"));
  for (const directory of ["blog", "docs", "src", "static"]) {
    await mkdir(join(root, directory));
  }
  for (const [path, content] of Object.entries(files)) {
    await writeFile(join(root, path), content);
  }
  return root;
}

function run(root) {
  return spawnSync(process.execPath, [script], {
    cwd: root,
    encoding: "utf-8",
  });
}

test("accepts supported image content", async () => {
  const root = await fixture({ "static/image.png": Buffer.from("89504e47", "hex") });
  try {
    assert.equal(run(root).status, 0);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("rejects blocked extensions and disguised signatures", async () => {
  const root = await fixture({
    "static/extension.heic": Buffer.from("safe"),
    "static/disguised-icns.png": Buffer.from("icnspayload"),
    "static/disguised-jxl.png": Buffer.from([0xff, 0x0a, 0x00]),
    "static/disguised-heif.png": Buffer.from(
      "000000186674797069736f6d0000000068656963",
      "hex",
    ),
  });
  try {
    const result = run(root);
    assert.equal(result.status, 1);
    assert.match(result.stderr, /extension\.heic/);
    assert.match(result.stderr, /disguised-icns\.png \(ICNS\)/);
    assert.match(result.stderr, /disguised-jxl\.png \(JPEG XL\)/);
    assert.match(result.stderr, /disguised-heif\.png \(HEIF\/AVIF\)/);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
