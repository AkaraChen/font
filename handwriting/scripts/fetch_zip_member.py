#!/usr/bin/env python3
"""Extract single members from a remote zip using HTTP range requests.

Why: the only Monaspace asset that ships **pre-patched Nerd Font** builds is
`monaspace-nerdfonts-*.zip` — 315 MiB for two 2.3 MiB OTFs. A zip's central
directory lives at the end of the file, so the member offsets can be read with
two small ranged GETs and each member inflated on its own.

Integrity is checked twice: the zip's own CRC-32 for the member, plus a pinned
sha256 of the extracted bytes (`--sha256`).

Usage:
  fetch_zip_member.py URL --member "path/in/zip.otf" --out FILE --sha256 HEX
  (repeat --member/--out/--sha256 triples in matching order)
"""

from __future__ import annotations

import argparse
import hashlib
import struct
import subprocess
import sys
import zlib
from pathlib import Path

EOCD_SIG = b"PK\x05\x06"
CD_SIG = b"PK\x01\x02"
TAIL_BYTES = 256 * 1024


def curl(args: list[str]) -> bytes:
    proc = subprocess.run(
        ["curl", "-fsSL", "--retry", "3", "--retry-delay", "2", *args],
        capture_output=True,
        check=True,
    )
    return proc.stdout


def remote_size(url: str) -> int:
    head = curl(["-I", url]).decode("utf-8", "replace")
    lengths = [
        line.split(":", 1)[1].strip()
        for line in head.splitlines()
        if line.lower().startswith("content-length")
    ]
    if not lengths:
        raise SystemExit("error: server did not report Content-Length")
    return int(lengths[-1])


def get_range(url: str, start: int, end: int) -> bytes:
    data = curl(["-r", f"{start}-{end}", url])
    want = end - start + 1
    if len(data) != want:
        raise SystemExit(
            f"error: range {start}-{end} returned {len(data)} bytes (wanted {want}); "
            "server may not support Range requests"
        )
    return data


def read_central_directory(url: str, size: int) -> dict[str, tuple[int, int, int, int]]:
    tail = get_range(url, max(0, size - TAIL_BYTES), size - 1)
    idx = tail.rfind(EOCD_SIG)
    if idx < 0:
        raise SystemExit("error: end-of-central-directory not found (zip64 or truncated?)")
    cd_size, cd_offset = struct.unpack("<II", tail[idx + 12 : idx + 20])
    if cd_size == 0xFFFFFFFF or cd_offset == 0xFFFFFFFF:
        raise SystemExit("error: zip64 central directory not supported")
    cd = get_range(url, cd_offset, cd_offset + cd_size - 1)

    entries: dict[str, tuple[int, int, int, int]] = {}
    pos = 0
    while pos < len(cd) and cd[pos : pos + 4] == CD_SIG:
        (method,) = struct.unpack("<H", cd[pos + 10 : pos + 12])
        crc, csize, _usize = struct.unpack("<III", cd[pos + 16 : pos + 28])
        nlen, elen, clen = struct.unpack("<HHH", cd[pos + 28 : pos + 34])
        (local_offset,) = struct.unpack("<I", cd[pos + 42 : pos + 46])
        name = cd[pos + 46 : pos + 46 + nlen].decode("utf-8", "replace")
        entries[name] = (method, crc, csize, local_offset)
        pos += 46 + nlen + elen + clen
    return entries


def extract(url: str, entry: tuple[int, int, int, int]) -> bytes:
    method, crc, csize, local_offset = entry
    header = get_range(url, local_offset, local_offset + 29)
    if header[:4] != b"PK\x03\x04":
        raise SystemExit("error: bad local file header")
    nlen, elen = struct.unpack("<HH", header[26:30])
    start = local_offset + 30 + nlen + elen
    raw = get_range(url, start, start + csize - 1)
    if method == 0:
        data = raw
    elif method == 8:
        data = zlib.decompress(raw, -15)
    else:
        raise SystemExit(f"error: unsupported compression method {method}")
    if zlib.crc32(data) & 0xFFFFFFFF != crc:
        raise SystemExit("error: CRC-32 mismatch for member")
    return data


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("url")
    ap.add_argument("--member", action="append", required=True)
    ap.add_argument("--out", action="append", type=Path, required=True)
    ap.add_argument("--sha256", action="append", default=[])
    args = ap.parse_args()

    if len(args.member) != len(args.out):
        ap.error("--member and --out must be given the same number of times")
    if args.sha256 and len(args.sha256) != len(args.member):
        ap.error("--sha256 must match the number of --member flags")

    shas = args.sha256 or [None] * len(args.member)
    wanted = list(zip(args.member, args.out, shas))

    pending = []
    for member, out, sha in wanted:
        cached = (
            out.exists()
            and sha is not None
            and hashlib.sha256(out.read_bytes()).hexdigest() == sha
        )
        if cached:
            print(f"cached {out}", file=sys.stderr)
        else:
            pending.append((member, out, sha))
    if not pending:
        return 0

    size = remote_size(args.url)
    entries = read_central_directory(args.url, size)
    print(f"remote zip: {size} bytes, {len(entries)} members", file=sys.stderr)

    for member, out, sha in pending:
        if member not in entries:
            print(f"error: member not in zip: {member}", file=sys.stderr)
            near = [n for n in entries if Path(member).name.split("-")[0] in n][:5]
            if near:
                print(f"  candidates: {near}", file=sys.stderr)
            return 1
        data = extract(args.url, entries[member])
        digest = hashlib.sha256(data).hexdigest()
        if sha is not None and sha != digest:
            print(
                f"error: sha256 mismatch for {member}\n"
                f"  expected {sha}\n  got      {digest}",
                file=sys.stderr,
            )
            return 1
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        print(f"extracted {out} ({len(data)} bytes, sha256 {digest[:16]}…)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
