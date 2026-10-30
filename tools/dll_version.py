#!/usr/bin/env python3
"""Print a DLL's real version and hash, because the file name proves nothing.

A replaced nvngx_dlssnr.dll is a measurement input: `2.1ms against 3.8ms` means nothing if the
next reader cannot tell which binary produced which number. This reads the version resource out
of the PE itself - the same fields the 310.8.16.0 investigation had to read to discover that the
bundled DLL is 310.8.0.0 - and prints the sha256 beside it.

Usage:
    python tools/dll_version.py native/nvngx_dlssnr.dll

Exit 0 on success. Exit 2 if the file is missing or carries no version resource, which is the
useful answer when a copy has gone wrong.
"""
import hashlib
import struct
import sys
from pathlib import Path

RT_VERSION = 16
VS_FIXEDFILEINFO = 0xFEEF04BD


def _rva_to_offset(pe: bytes, rva: int) -> int:
    """Map an RVA to a file offset using the section table."""
    e_lfanew = struct.unpack_from("<I", pe, 0x3C)[0]
    sections = struct.unpack_from("<H", pe, e_lfanew + 6)[0]
    optional_size = struct.unpack_from("<H", pe, e_lfanew + 20)[0]
    table = e_lfanew + 24 + optional_size
    for i in range(sections):
        base = table + i * 40
        virtual_size, virtual_address, raw_size, raw_ptr = struct.unpack_from("<IIII", pe, base + 8)
        if virtual_address <= rva < virtual_address + max(virtual_size, raw_size):
            return raw_ptr + (rva - virtual_address)
    return rva


def find_version_resource(pe: bytes) -> bytes | None:
    """The RT_VERSION blob, found by walking the resource directory tree."""
    e_lfanew = struct.unpack_from("<I", pe, 0x3C)[0]
    magic = struct.unpack_from("<H", pe, e_lfanew + 24)[0]
    # Data directories live INSIDE the optional header, 112 bytes in for PE32+ and 96 for
    # PE32 - not after it. Offsetting from the section table instead reads the first section
    # header as a directory and every lookup comes back empty.
    directories = e_lfanew + 24 + (112 if magic == 0x20B else 96)
    if struct.unpack_from("<I", pe, directories)[0] == 0:
        return None
    resource_rva = struct.unpack_from("<I", pe, directories + 2 * 8)[0]
    res = _rva_to_offset(pe, resource_rva)

    def entries(offset: int, count: int, base: int):
        for i in range(count):
            name, target = struct.unpack_from("<II", pe, offset + i * 8)
            yield name, target

    named, count = struct.unpack_from("<HH", pe, res + 12)
    type_entry = None
    for name, target in entries(res + 16 + named * 8, count, res):
        if name == RT_VERSION:
            type_entry = target & 0x7FFFFFFF      # a subdirectory: high bit set
            break
    if type_entry is None:
        return None

    name_off, count = struct.unpack_from("<HH", pe, res + type_entry + 12)
    first = None
    for _, target in entries(res + type_entry + 16 + name_off * 8, count, res):
        first = target & 0x7FFFFFFF          # a directory, so the high bit is set
        break
    if first is None:
        return None

    lang_off, count = struct.unpack_from("<HH", pe, res + first + 12)
    data_entry = None
    for _, target in entries(res + first + 16 + lang_off * 8, count, res):
        data_entry = target          # first language wins
        break
    if data_entry is None:
        return None

    data_rva, data_size = struct.unpack_from("<II", pe, res + data_entry)
    offset = _rva_to_offset(pe, data_rva)
    return pe[offset:offset + data_size]


def fixed_file_info(blob: bytes) -> dict | None:
    """Walk the VS_VERSIONINFO structure to the fixed file info."""
    pos = 0

    def read_node(pos: int):
        length, value_length, kind = struct.unpack_from("<HHH", pe := blob, pos)
        key_chars = []
        p = pos + 6
        while p + 2 <= pos + length:
            ch = struct.unpack_from("<H", pe, p)[0]
            p += 2
            if ch == 0:
                break
            key_chars.append(chr(ch))
        key = "".join(key_chars)
        if p % 4:
            p += 4 - (p % 4)
        value = pe[p:p + value_length]
        return key, value, pos + length, kind

    key, value, end, _ = read_node(pos)
    if key != "VS_VERSION_INFO":
        return None
    if len(value) < 52:
        return None
    sig, struc_version = struct.unpack_from("<II", value, 0)
    if sig != VS_FIXEDFILEINFO:
        return None
    ms, ls = struct.unpack_from("<II", value, 8)
    pms, pls = struct.unpack_from("<II", value, 16)
    return {
        "file_version": f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}",
        "product_version": f"{pms >> 16}.{pms & 0xFFFF}.{pls >> 16}.{pls & 0xFFFF}",
        "struc_version": struc_version,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: dll_version.py PATH_TO_DLL", file=sys.stderr)
        return 2
    path = Path(argv[0])
    if not path.is_file():
        print(f"{path}: no such file", file=sys.stderr)
        return 2

    data = path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    print(f"file    {path}")
    print(f"bytes   {len(data):,}")
    print(f"sha256  {sha}")

    blob = find_version_resource(data)
    if blob is None:
        print("version (no RT_VERSION resource: this is not a versioned DLL, or the copy is "
              "truncated)", file=sys.stderr)
        return 2
    info = fixed_file_info(blob)
    if info is None:
        print("version (the RT_VERSION blob is not a VS_FIXEDFILEINFO)", file=sys.stderr)
        return 2
    print(f"version {info['file_version']}")
    print(f"product {info['product_version']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))