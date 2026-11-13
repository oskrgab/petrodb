/**
 * List a Dataset's parquet tree straight from disk, the way the Glances command
 * does (`list_files` in scripts/site/glances.py). The site uses it for a Dataset
 * whose tree is built in CI rather than committed (Petrobras 3W), so the build
 * needs neither Python nor a parquet library: sizes come from the file system,
 * row counts from each file's footer.
 */
import { closeSync, existsSync, openSync, readFileSync, readSync, readdirSync, statSync } from "node:fs";
import { resolve } from "node:path";
import type { TableFile } from "../types.ts";

/** One table of a listing; the shape of each entry in a committed `files.json`. */
export interface TreeTable {
  name: string;
  kind: "single" | "multi";
  path?: string;
  manifest?: string;
  bytes: number;
  rows: number;
  files?: TableFile[];
}

/**
 * A directory holding a Manifest is one Multi-parquet table; any other
 * `*.parquet` at the Dataset root is a single-file table. Null when the tree
 * is not on disk.
 */
export function listTree(root: string): TreeTable[] | null {
  if (!existsSync(root)) return null;
  const entries = readdirSync(root, { withFileTypes: true }).sort((a, b) => (a.name < b.name ? -1 : 1));
  const tables: TreeTable[] = [];
  for (const e of entries) {
    if (!e.isFile() || !e.name.endsWith(".parquet")) continue;
    const file = resolve(root, e.name);
    tables.push({
      name: e.name.replace(/\.parquet$/, ""),
      kind: "single",
      path: e.name,
      bytes: statSync(file).size,
      rows: parquetRows(file),
    });
  }
  for (const e of entries) {
    const manifest = resolve(root, e.name, "_files.json");
    if (!e.isDirectory() || !existsSync(manifest)) continue;
    const files = (JSON.parse(readFileSync(manifest, "utf8")) as string[]).map((rel) => {
      const file = resolve(root, e.name, rel);
      return { path: `${e.name}/${rel}`, bytes: statSync(file).size, rows: parquetRows(file) };
    });
    tables.push({
      name: e.name,
      kind: "multi",
      manifest: `${e.name}/_files.json`,
      bytes: files.reduce((sum, f) => sum + f.bytes, 0),
      rows: files.reduce((sum, f) => sum + f.rows, 0),
      files,
    });
  }
  return tables;
}

/**
 * `num_rows` from a parquet file's footer: a Thrift (compact protocol)
 * FileMetaData whose field 3 is the row count. Only the footer is read.
 */
export function parquetRows(file: string): number {
  const fd = openSync(file, "r");
  try {
    const size = statSync(file).size;
    const tail = Buffer.alloc(8);
    readSync(fd, tail, 0, 8, size - 8);
    if (tail.toString("latin1", 4) !== "PAR1") throw new Error(`${file} is not a parquet file`);
    const length = tail.readUInt32LE(0);
    const footer = Buffer.alloc(length);
    readSync(fd, footer, 0, length, size - 8 - length);
    return new CompactReader(footer).fileMetaDataRows();
  } finally {
    closeSync(fd);
  }
}

class CompactReader {
  // No parameter properties: node --test strips types but cannot compile them.
  private readonly buf: Buffer;
  private at = 0;
  constructor(buf: Buffer) {
    this.buf = buf;
  }

  fileMetaDataRows(): number {
    let field = 0;
    for (;;) {
      const header = this.buf[this.at++];
      const type = header & 0x0f;
      if (type === 0) break;
      const delta = header >> 4;
      field = delta ? field + delta : this.zigzag(this.varint());
      if (field === 3 && type === 6) return Number(this.zigzag(this.varint()));
      this.skip(type);
    }
    throw new Error("parquet footer has no num_rows");
  }

  private varint(): bigint {
    let out = 0n;
    let shift = 0n;
    for (;;) {
      const byte = this.buf[this.at++];
      out |= BigInt(byte & 0x7f) << shift;
      if (!(byte & 0x80)) return out;
      shift += 7n;
    }
  }

  private zigzag(n: bigint): number {
    return Number((n >> 1n) ^ -(n & 1n));
  }

  private skip(type: number): void {
    switch (type) {
      case 1: // true
      case 2: // false
        return;
      case 3: // i8
        this.at += 1;
        return;
      case 4: // i16
      case 5: // i32
      case 6: // i64
        this.varint();
        return;
      case 7: // double
        this.at += 8;
        return;
      case 8: {
        // binary; read the length before moving `at`, which `+=` would read first
        const length = Number(this.varint());
        this.at += length;
        return;
      }
      case 9: // list
      case 10: {
        // set
        const header = this.buf[this.at++];
        const size = header >> 4 === 15 ? Number(this.varint()) : header >> 4;
        const element = header & 0x0f;
        for (let i = 0; i < size; i++) {
          if (element === 1 || element === 2) this.at += 1; // bools are one byte in a list
          else this.skip(element);
        }
        return;
      }
      case 11: {
        // map
        const size = Number(this.varint());
        if (!size) return;
        const kinds = this.buf[this.at++];
        for (let i = 0; i < size; i++) {
          this.skip(kinds >> 4);
          this.skip(kinds & 0x0f);
        }
        return;
      }
      case 12: {
        // struct
        for (;;) {
          const header = this.buf[this.at++];
          const t = header & 0x0f;
          if (t === 0) return;
          if (!(header >> 4)) this.varint();
          this.skip(t);
        }
      }
      default:
        throw new Error(`unknown thrift compact type ${type}`);
    }
  }
}
