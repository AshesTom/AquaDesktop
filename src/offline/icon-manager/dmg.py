#!/usr/bin/env python3
"""App icons out of a macOS disk image (.dmg), with no external tool.

Reads the UDIF image (raw, zlib, bzip2, LZMA, LZFSE and ADC chunks,
decompressed on demand), the HFS+ / HFSX or APFS volume inside it (files
compressed with decmpfs included), finds the `.app` bundles and gives each
one's icon: Info.plist's CFBundleIconFile in Contents/Resources (an
.icns), the bytes as they are.

    dmg.py list IMAGE.dmg           one "name<TAB>bundle path" line per app
    dmg.py extract IMAGE.dmg APP OUT.icns
"""

from __future__ import annotations

import bz2
import lzma
import plistlib
import struct
import sys
import zlib
from bisect import bisect_right
from collections import OrderedDict
from pathlib import PurePosixPath


class DmgError(Exception):
    pass


# ── LZVN / LZFSE (Apple's own compressors; not in the standard library) ──

def lzvn_decode(src: bytes, size: int | None = None) -> bytes:
    out = bytearray()
    i, n, d = 0, len(src), 0
    while i < n:
        op = src[i]
        if op >= 0xE0:
            if op == 0xE0:                       # large literal
                lit, i = src[i + 1] + 16, i + 2
            elif op < 0xF0:                      # small literal
                lit, i = op & 0x0F, i + 1
            else:                                # match with the previous distance
                if op == 0xF0:
                    m, i = src[i + 1] + 16, i + 2
                else:
                    m, i = op & 0x0F, i + 1
                _copy(out, d, m)
                continue
            out += src[i:i + lit]
            i += lit
            continue
        if 0xA0 <= op < 0xC0:                    # medium distance
            b = src[i + 1] | src[i + 2] << 8
            lit, m, d = (op >> 3) & 3, ((op & 7) << 2 | (b & 3)) + 3, b >> 2
            i += 3
        elif 0x70 <= op < 0x80:
            raise DmgError("LZVN: undefined opcode")
        else:
            low = op & 7
            lit, m = op >> 6, ((op >> 3) & 7) + 3
            if low == 7:                         # large distance
                d, i = src[i + 1] | src[i + 2] << 8, i + 3
            elif low == 6:
                if op == 0x06:                   # end of stream
                    break
                if op < 0x40:
                    if op in (0x0E, 0x16):       # nop
                        i += 1
                        continue
                    raise DmgError("LZVN: undefined opcode")
                i += 1                           # previous distance
            else:                                # small distance
                d, i = (low << 8) | src[i + 1], i + 2
        out += src[i:i + lit]
        i += lit
        _copy(out, d, m)
    return bytes(out if size is None else out[:size])


def _copy(out: bytearray, dist: int, length: int) -> None:
    if dist <= 0 or dist > len(out):
        raise DmgError("bad match distance")
    start = len(out) - dist
    if dist >= length:
        out += out[start:start + length]
    else:
        for k in range(length):
            out.append(out[start + k])


def _bases(extra: list[int]) -> list[int]:
    base = [0]
    for e in extra[:-1]:
        base.append(base[-1] + (1 << e))
    return base


_L_EXTRA = [0] * 16 + [2, 3, 5, 8]
_M_EXTRA = [0] * 16 + [3, 5, 8, 11]
_D_EXTRA = [e for e in range(16) for _ in range(4)]
_L_BASE, _M_BASE, _D_BASE = _bases(_L_EXTRA), _bases(_M_EXTRA), _bases(_D_EXTRA)
_FREQ_NBITS = [2, 3, 2, 5, 2, 3, 2, 8, 2, 3, 2, 5, 2, 3, 2, 14] * 2
_FREQ_VALUE = [0, 2, 1, 4, 0, 3, 1, -1, 0, 2, 1, 5, 0, 3, 1, -1,
               0, 2, 1, 6, 0, 3, 1, -1, 0, 2, 1, 7, 0, 3, 1, -1]


def _fse_table(nstates: int, freqs: list[int], extra=None, base=None) -> list[tuple]:
    """Entries (symbol or value base, bits, delta, value bits) per state."""
    table = []
    nbits_states = nstates.bit_length()
    for sym, f in enumerate(freqs):
        if not f:
            continue
        k = nbits_states - f.bit_length()        # N <= f << k < 2N
        j0 = ((2 * nstates) >> k) - f
        vbits = extra[sym] if extra else 0
        value = base[sym] if base else sym
        for j in range(f):
            if j < j0:
                table.append((value, k + vbits, ((f + j) << k) - nstates, vbits))
            else:
                table.append((value, k - 1 + vbits, (j - j0) << (k - 1), vbits))
    if len(table) > nstates:
        raise DmgError("LZFSE: bad frequency table")
    return table


class _BackBits:
    """FSE's backward bit stream: the last bytes are read first."""

    def __init__(self, buf: bytes, start: int, end: int, extra_bits: int):
        self.buf, self.start, self.pos = buf, start, end
        if extra_bits:
            self.pos -= 8
            self.accum = int.from_bytes(buf[self.pos:self.pos + 8], "little")
            self.nbits = 64 + extra_bits
        else:
            self.pos -= 7
            self.accum = int.from_bytes(buf[self.pos:self.pos + 7], "little")
            self.nbits = 56
        if self.pos < start or self.accum >> self.nbits:
            raise DmgError("LZFSE: bad bit stream")

    def flush(self) -> None:
        nbits = (63 - self.nbits) & ~7
        nbytes = nbits >> 3
        if nbytes:
            self.pos -= nbytes
            if self.pos < self.start:
                raise DmgError("LZFSE: bit stream overrun")
            incoming = int.from_bytes(self.buf[self.pos:self.pos + nbytes], "little")
            self.accum = (self.accum << nbits) | incoming
            self.nbits += nbits

    def pull(self, n: int) -> int:
        self.nbits -= n
        result = self.accum >> self.nbits
        self.accum &= (1 << self.nbits) - 1
        return result


def lzfse_decode(src: bytes) -> bytes:
    out = bytearray()
    i = 0
    while True:
        magic = src[i:i + 4]
        if magic == b"bvx$":
            return bytes(out)
        if magic == b"bvx-":
            n = struct.unpack_from("<I", src, i + 4)[0]
            out += src[i + 8:i + 8 + n]
            i += 8 + n
        elif magic == b"bvxn":
            n, payload = struct.unpack_from("<II", src, i + 4)
            out += lzvn_decode(src[i + 12:i + 12 + payload], n)
            i += 12 + payload
        elif magic == b"bvx2":
            i = _lzfse_v2_block(src, i, out)
        else:
            raise DmgError("LZFSE: unknown block %r" % magic)


def _lzfse_v2_block(src: bytes, i: int, out: bytearray) -> int:
    n_raw, v0, v1, v2 = struct.unpack_from("<IQQQ", src, i + 4)
    field = lambda v, off, n: (v >> off) & ((1 << n) - 1)  # noqa: E731
    n_literals, n_lit_payload = field(v0, 0, 20), field(v0, 20, 20)
    n_matches, literal_bits = field(v0, 40, 20), field(v0, 60, 3) - 7
    lit_states = [field(v1, 10 * k, 10) for k in range(4)]
    n_lmd_payload, lmd_bits = field(v1, 40, 20), field(v1, 60, 3) - 7
    header_size = field(v2, 0, 32)
    l_state, m_state, d_state = field(v2, 32, 10), field(v2, 42, 10), field(v2, 52, 10)

    freqs = []
    p, end = i + 32, i + header_size
    accum = accum_bits = 0
    for _ in range(20 + 20 + 64 + 256):
        while p < end and accum_bits + 8 <= 32:
            accum |= src[p] << accum_bits
            accum_bits += 8
            p += 1
        b = accum & 31
        nb = _FREQ_NBITS[b]
        if nb == 8:
            value = 8 + ((accum >> 4) & 0xF)
        elif nb == 14:
            value = 24 + ((accum >> 4) & 0x3FF)
        else:
            value = _FREQ_VALUE[b]
        if nb > accum_bits:
            raise DmgError("LZFSE: bad header")
        accum >>= nb
        accum_bits -= nb
        freqs.append(value)
    l_freq, m_freq, d_freq, lit_freq = freqs[:20], freqs[20:40], freqs[40:104], freqs[104:]

    lit_table = _fse_table(1024, lit_freq)
    payload = i + header_size
    # Its refills may reach below the payload (into the header), as lzfse's
    # own decoder bounds them by the start of the input only.
    bits = _BackBits(src, 0, payload + n_lit_payload, literal_bits)
    literals = bytearray()
    states = lit_states[:]
    for _ in range(0, n_literals, 4):
        bits.flush()
        for k in range(4):
            sym, nb, delta, _v = lit_table[states[k]]
            states[k] = delta + bits.pull(nb)
            literals.append(sym)

    lmd = payload + n_lit_payload
    l_table = _fse_table(64, l_freq, _L_EXTRA, _L_BASE)
    m_table = _fse_table(64, m_freq, _M_EXTRA, _M_BASE)
    d_table = _fse_table(256, d_freq, _D_EXTRA, _D_BASE)
    bits = _BackBits(src, lmd, lmd + n_lmd_payload, lmd_bits)
    lit_pos, dist = 0, -1
    start = len(out)

    def value(table, state):
        base, nb, delta, vbits = table[state]
        got = bits.pull(nb)
        return delta + (got >> vbits), base + (got & ((1 << vbits) - 1))

    for _ in range(n_matches):
        bits.flush()
        l_state, lit = value(l_table, l_state)
        m_state, m = value(m_table, m_state)
        d_state, new_dist = value(d_table, d_state)
        dist = new_dist or dist
        out += literals[lit_pos:lit_pos + lit]
        lit_pos += lit
        if m:
            _copy(out, dist, m)
    if len(out) - start != n_raw:
        raise DmgError("LZFSE: block size mismatch")
    return lmd + n_lmd_payload


def adc_decode(src: bytes) -> bytes:
    out = bytearray()
    i, n = 0, len(src)
    while i < n:
        b = src[i]
        if b & 0x80:
            length = (b & 0x7F) + 1
            out += src[i + 1:i + 1 + length]
            i += 1 + length
            continue
        if b & 0x40:
            length, dist = (b & 0x3F) + 4, (src[i + 1] << 8 | src[i + 2])
            i += 3
        else:
            length, dist = ((b & 0x3F) >> 2) + 3, ((b & 3) << 8 | src[i + 1])
            i += 2
        _copy(out, dist + 1, length)
    return bytes(out)


# ── UDIF ──────────────────────────────────────────────────────────────

SECTOR = 512


class Udif:
    """The disk inside a .dmg, read like a file; chunks are decompressed
    when first touched (a few kept)."""

    def __init__(self, path: str):
        self.f = open(path, "rb")
        self.f.seek(0, 2)
        size = self.f.tell()
        if size < 512:
            raise DmgError("not a disk image")
        self.f.seek(size - 512)
        koly = self.f.read(512)
        self.chunks = []        # (start sector, sector count, type, offset, length)
        self.partitions = []    # (name, start byte)
        if koly[:4] != b"koly":
            # A raw image (hdiutil UDTO / CDR): sectors as they are.
            self.chunks.append((0, size // SECTOR, 1, 0, size))
            self.partitions.append(("raw", 0))
        else:
            data_fork = struct.unpack_from(">Q", koly, 0x18)[0]
            xml_off, xml_len = struct.unpack_from(">QQ", koly, 0xD8)
            if not xml_len:
                raise DmgError("old disk image without a property list")
            self.f.seek(xml_off)
            plist = plistlib.loads(self.f.read(xml_len))
            for entry in plist.get("resource-fork", {}).get("blkx", []):
                self._add_blkx(entry.get("Name", ""), entry["Data"], data_fork)
        self.chunks.sort()
        self.starts = [c[0] for c in self.chunks]
        self.size = max((c[0] + c[1]) for c in self.chunks) * SECTOR
        self.cache: OrderedDict = OrderedDict()

    def _add_blkx(self, name: str, mish: bytes, data_fork: int) -> None:
        if mish[:4] != b"mish":
            return
        first, _count, data_offset = struct.unpack_from(">QQQ", mish, 8)
        n = struct.unpack_from(">I", mish, 200)[0]
        self.partitions.append((name, first * SECTOR))
        for k in range(n):
            ctype, _c, sec, count, off, length = struct.unpack_from(">IIQQQQ", mish, 204 + 40 * k)
            if ctype in (0x7FFFFFFE, 0xFFFFFFFF) or not count:
                continue
            self.chunks.append((first + sec, count, ctype, data_fork + data_offset + off, length))

    def _chunk(self, index: int) -> bytes:
        if index in self.cache:
            self.cache.move_to_end(index)
            return self.cache[index]
        _start, count, ctype, off, length = self.chunks[index]
        size = count * SECTOR
        if ctype in (0, 2):
            data = bytes(size)
        else:
            self.f.seek(off)
            raw = self.f.read(length)
            if ctype == 1:
                data = raw
            elif ctype == 0x80000005:
                data = zlib.decompress(raw)
            elif ctype == 0x80000006:
                data = bz2.decompress(raw)
            elif ctype == 0x80000008:
                data = lzma.LZMADecompressor().decompress(raw)
            elif ctype == 0x80000007:
                data = lzfse_decode(raw)
            elif ctype == 0x80000004:
                data = adc_decode(raw)
            else:
                raise DmgError("unsupported chunk type 0x%08x" % ctype)
        data = data[:size].ljust(size, b"\0")
        self.cache[index] = data
        if len(self.cache) > 24:
            self.cache.popitem(last=False)
        return data

    def read(self, offset: int, length: int) -> bytes:
        out = bytearray()
        end = offset + length
        while offset < end:
            sector = offset // SECTOR
            index = bisect_right(self.starts, sector) - 1
            if index < 0 or sector >= self.chunks[index][0] + self.chunks[index][1]:
                piece = bytes(min(end - offset, SECTOR - offset % SECTOR))   # a hole
            else:
                rel = offset - self.chunks[index][0] * SECTOR
                piece = self._chunk(index)[rel:rel + end - offset]
            out += piece
            offset += len(piece)
        return bytes(out)


class Slice:
    """A partition of the disk."""

    def __init__(self, disk, base: int):
        self.disk, self.base = disk, base

    def read(self, offset: int, length: int) -> bytes:
        return self.disk.read(self.base + offset, length)


# ── HFS+ ──────────────────────────────────────────────────────────────

class Node:
    __slots__ = ("name", "kind", "children", "data", "fid")

    def __init__(self, name, kind, fid, data=None):
        self.name, self.kind, self.fid, self.data = name, kind, fid, data
        self.children: dict[str, Node] = {}


class Volume:
    """What both file systems give: a tree of names and a way to read a file."""

    root: Node

    def lookup(self, path: str, follow: bool = True) -> Node | None:
        node, parts = self.root, [p for p in path.strip("/").split("/") if p]
        for depth, part in enumerate(parts):
            child = node.children.get(part)
            if child is None:
                lower = part.lower()
                child = next((c for n, c in node.children.items() if n.lower() == lower), None)
            if child is None:
                return None
            if child.kind == "link" and (follow or depth < len(parts) - 1):
                target = self.read_file(child).decode("utf-8", "replace")
                here = "/".join(parts[:depth])
                resolved = target if target.startswith("/") else here + "/" + target
                child = self.lookup(_normpath(resolved))
                if child is None:
                    return None
            node = child
        return node

    def read_file(self, node: Node) -> bytes:
        raise NotImplementedError


def _normpath(path: str) -> str:
    out: list[str] = []
    for part in path.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if out:
                out.pop()
        else:
            out.append(part)
    return "/".join(out)


class Hfs(Volume):
    def __init__(self, dev):
        self.dev = dev
        vh = dev.read(1024, 512)
        if vh[:2] not in (b"H+", b"HX"):
            raise DmgError("not HFS+")
        self.block = struct.unpack_from(">I", vh, 40)[0]
        self.extents_fork = self._fork(vh, 192, 3)
        self.catalog_fork = self._fork(vh, 272, 4)
        self.attributes_fork = self._fork(vh, 352, 8)
        self._overflow: dict | None = None
        self.attrs: dict[int, dict[str, bytes]] = {}
        self._load_catalog()

    @staticmethod
    def _fork(buf: bytes, off: int, fid: int) -> tuple:
        size, _clump, total = struct.unpack_from(">QII", buf, off)
        extents = [struct.unpack_from(">II", buf, off + 16 + 8 * k) for k in range(8)]
        return (fid, size, total, [e for e in extents if e[1]])

    def _fork_extents(self, fork: tuple, rsrc: bool = False) -> list:
        fid, _size, total, extents = fork
        have = sum(e[1] for e in extents)
        if have < total and fid != 3:
            more = self._overflow_extents().get((fid, 0xFF if rsrc else 0), [])
            extents = extents + [e for start, ex in sorted(more) for e in ex if e[1]]
        return extents

    def _read_fork(self, fork: tuple, rsrc: bool = False) -> bytes:
        size = fork[1]
        out = bytearray()
        for start, count in self._fork_extents(fork, rsrc):
            if len(out) >= size:
                break
            out += self.dev.read(start * self.block, count * self.block)
        return bytes(out[:size])

    def _leaves(self, fork: tuple):
        data = self._read_fork(fork)
        if not data:
            return
        node_size = struct.unpack_from(">H", data, 14 + 18)[0]
        node = struct.unpack_from(">I", data, 14 + 10)[0]      # first leaf
        seen = set()
        while node and node not in seen:
            seen.add(node)
            base = node * node_size
            flink, _blink, kind, _h, nrec = struct.unpack_from(">IIbBH", data, base)
            if kind != -1:
                break
            offs = [struct.unpack_from(">H", data, base + node_size - 2 * (k + 1))[0]
                    for k in range(nrec + 1)]
            for k in range(nrec):
                yield data[base + offs[k]:base + offs[k + 1]]
            node = flink

    def _overflow_extents(self) -> dict:
        if self._overflow is None:
            self._overflow = {}
            for rec in self._leaves(self.extents_fork):
                _klen, ftype, _pad, fid, start = struct.unpack_from(">HBBII", rec, 0)
                ex = [struct.unpack_from(">II", rec, 12 + 8 * k) for k in range(8)]
                self._overflow.setdefault((fid, ftype), []).append((start, ex))
        return self._overflow

    def _load_catalog(self) -> None:
        folders: dict[int, Node] = {}
        entries = []
        for rec in self._leaves(self.catalog_fork):
            klen, parent, nlen = struct.unpack_from(">HIH", rec, 0)
            name = rec[8:8 + 2 * nlen].decode("utf-16-be", "replace")
            body = rec[2 + klen:]
            body = body[1:] if (2 + klen) % 2 else body       # records are 2-aligned
            rtype = struct.unpack_from(">h", body, 0)[0]
            if rtype == 1:
                fid = struct.unpack_from(">I", body, 8)[0]
                folders[fid] = Node(name, "dir", fid)
                entries.append((parent, folders[fid]))
            elif rtype == 2:
                fid = struct.unpack_from(">I", body, 8)[0]
                flags = body[41]
                mode = struct.unpack_from(">H", body, 42)[0]
                special = struct.unpack_from(">I", body, 44)[0]
                ftype = body[48:56]
                kind = "link" if mode & 0o170000 == 0o120000 else "file"
                info = {"data": self._fork(body, 88, fid), "rsrc": self._fork(body, 168, fid),
                        "compressed": bool(flags & 0x20)}
                if ftype == b"hlnkhfs+":
                    info["inode"] = special
                entries.append((parent, Node(name, kind, fid, info)))
        root = folders.get(2) or Node("", "dir", 2)
        for parent, node in entries:
            if parent in folders and node is not root:
                folders[parent].children[node.name] = node
        self.root = root
        self.private = root.children.get("\0\0\0\0HFS+ Private Data")

    def _xattr(self, fid: int, name: str) -> bytes | None:
        if not self.attrs and self.attributes_fork[1]:
            for rec in self._leaves(self.attributes_fork):
                klen, _pad, afid, _start, nlen = struct.unpack_from(">HHIIH", rec, 0)
                aname = rec[14:14 + 2 * nlen].decode("utf-16-be", "replace")
                body = rec[2 + klen:]
                if struct.unpack_from(">I", body, 0)[0] == 0x10:      # inline data
                    size = struct.unpack_from(">I", body, 12)[0]
                    self.attrs.setdefault(afid, {})[aname] = body[16:16 + size]
            self.attrs.setdefault(-1, {})
        return self.attrs.get(fid, {}).get(name)

    def read_file(self, node: Node) -> bytes:
        info = node.data
        if "inode" in info and self.private:
            target = self.private.children.get("iNode%d" % info["inode"])
            if target:
                node, info = target, target.data
        if info["compressed"]:
            header = self._xattr(node.fid, "com.apple.decmpfs")
            if header:
                return decmpfs(header, lambda: self._read_fork(info["rsrc"], True))
        return self._read_fork(info["data"])


def decmpfs(header: bytes, resource_fork) -> bytes:
    """A file compressed by the file system (HFS+ and APFS alike)."""
    magic, ctype, size = struct.unpack_from("<4sIQ", header, 0)
    if magic != b"fpmc":
        raise DmgError("bad decmpfs header")
    inline = header[16:]
    if ctype == 1:
        return inline[:size]
    if ctype == 3:
        return inline[1:1 + size] if inline[:1] and inline[0] & 0x0F == 0x0F else zlib.decompress(inline)
    if ctype == 7:
        return inline[1:1 + size] if inline[:1] == b"\x06" else lzvn_decode(inline, size)
    if ctype == 11:
        return inline[1:1 + size] if inline[:1] == b"\xff" else lzfse_decode(inline)
    if ctype == 9:
        return inline[1:1 + size] if inline[:1] == b"\xff" else bytes(inline)
    rsrc = resource_fork()
    out = bytearray()
    if ctype == 4:                                       # zlib, resource fork
        data_off = struct.unpack_from(">I", rsrc, 0)[0]
        base = data_off + 4
        count = struct.unpack_from("<I", rsrc, base)[0]
        for k in range(count):
            off, length = struct.unpack_from("<II", rsrc, base + 4 + 8 * k)
            chunk = rsrc[base + off:base + off + length]
            out += chunk[1:] if chunk[:1] and chunk[0] & 0x0F == 0x0F else zlib.decompress(chunk)
    elif ctype in (8, 12, 10):                           # LZVN / LZFSE / raw, resource fork
        first = struct.unpack_from("<I", rsrc, 0)[0]
        offsets = [struct.unpack_from("<I", rsrc, 4 * k)[0] for k in range(first // 4)]
        for a, b in zip(offsets, offsets[1:]):
            chunk = rsrc[a:b]
            if ctype == 10 or chunk[:1] == (b"\x06" if ctype == 8 else b"\xff"):
                out += chunk if ctype == 10 else chunk[1:]          # stored as is
            elif ctype == 8:
                out += lzvn_decode(chunk, 65536)
            else:
                out += lzfse_decode(chunk)
    else:
        raise DmgError("unsupported file compression %d" % ctype)
    return bytes(out[:size])


# ── APFS ──────────────────────────────────────────────────────────────

class Apfs(Volume):
    def __init__(self, dev):
        self.dev = dev
        nx = dev.read(0, 4096)
        if nx[32:36] != b"NXSB":
            raise DmgError("not APFS")
        self.bs = struct.unpack_from("<I", nx, 36)[0]
        nx = self._latest_superblock(nx)
        omap = self._block(struct.unpack_from("<Q", nx, 160)[0])
        self.nx_omap = self._omap(struct.unpack_from("<Q", omap, 48)[0])
        volumes = [v for v in struct.unpack_from("<100Q", nx, 184) if v]
        if not volumes:
            raise DmgError("APFS container without a volume")
        apsb = self._block(self.nx_omap[volumes[0]])
        if apsb[32:36] != b"APSB":
            raise DmgError("bad APFS volume")
        vomap = self._block(struct.unpack_from("<Q", apsb, 128)[0])
        self.v_omap = self._omap(struct.unpack_from("<Q", vomap, 48)[0])
        self._load_tree(struct.unpack_from("<Q", apsb, 136)[0])

    def _block(self, addr: int) -> bytes:
        return self.dev.read(addr * self.bs, self.bs)

    def _latest_superblock(self, nx: bytes) -> bytes:
        desc_blocks, _db, desc_base = struct.unpack_from("<IIQ", nx, 104)
        best, best_xid = nx, struct.unpack_from("<Q", nx, 16)[0]
        if desc_blocks & 0x80000000:
            return nx
        for k in range(desc_blocks):
            blk = self._block(desc_base + k)
            if blk[32:36] == b"NXSB":
                xid = struct.unpack_from("<Q", blk, 16)[0]
                if xid > best_xid:
                    best, best_xid = blk, xid
        return best

    def _node_entries(self, node: bytes):
        """(key bytes, value bytes) of a B-tree node; values of a child index
        on non-leaf nodes."""
        flags, level, nkeys = struct.unpack_from("<HHI", node, 32)
        toc_off, toc_len = struct.unpack_from("<HH", node, 40)
        keys_start = 56 + toc_off + toc_len
        vals_end = len(node) - (40 if flags & 1 else 0)
        fixed = flags & 4
        for k in range(nkeys):
            if fixed:
                ko, vo = struct.unpack_from("<HH", node, 56 + toc_off + 4 * k)
                kl, vl = 16, (16 if level == 0 else 8)
            else:
                ko, kl, vo, vl = struct.unpack_from("<HHHH", node, 56 + toc_off + 8 * k)
            if vo == 0xFFFF:
                continue
            yield node[keys_start + ko:keys_start + ko + kl], node[vals_end - vo:vals_end - vo + vl], level

    def _omap(self, root: int) -> dict:
        """Every (oid -> physical address) of an object map, latest xid."""
        found: dict[int, tuple] = {}

        def walk(addr):
            for key, val, level in self._node_entries(self._block(addr)):
                if level:
                    walk(struct.unpack_from("<Q", val, 0)[0])
                else:
                    oid, xid = struct.unpack_from("<QQ", key, 0)
                    flags, _size, paddr = struct.unpack_from("<IIQ", val, 0)
                    if flags & 1:                                  # deleted
                        continue
                    if oid not in found or xid > found[oid][0]:
                        found[oid] = (xid, paddr)
        walk(root)
        return {oid: v[1] for oid, v in found.items()}

    def _load_tree(self, root_oid: int) -> None:
        nodes: dict[int, Node] = {}
        dirents = []
        self.inodes: dict[int, tuple] = {}         # oid -> (dstream id, size, flags, mode)
        self.extents: dict[int, list] = {}         # dstream id -> [(logical, length, block)]
        self.xattrs: dict[int, dict] = {}

        def walk(oid):
            for key, val, level in self._node_entries(self._block(self.v_omap[oid])):
                if level:
                    walk(struct.unpack_from("<Q", val, 0)[0])
                    continue
                hdr = struct.unpack_from("<Q", key, 0)[0]
                obj, kind = hdr & ((1 << 60) - 1), hdr >> 60
                if kind == 9:                                     # directory record
                    if len(key) >= 12 and 12 + (struct.unpack_from("<I", key, 8)[0] & 0x3FF) == len(key):
                        name = key[12:-1]
                    else:
                        nlen = struct.unpack_from("<H", key, 8)[0]
                        name = key[10:10 + nlen - 1]
                    fid, _added, flags = struct.unpack_from("<QQH", val, 0)
                    dirents.append((obj, name.decode("utf-8", "replace"), fid, flags & 0xF))
                elif kind == 3:                                   # inode
                    private = struct.unpack_from("<Q", val, 8)[0]
                    bsd_flags = struct.unpack_from("<I", val, 68)[0]
                    mode = struct.unpack_from("<H", val, 80)[0]
                    size = 0
                    if len(val) > 92:
                        nx, _used = struct.unpack_from("<HH", val, 92)
                        p = 96 + 4 * nx
                        for x in range(nx):
                            xtype, _xf, xsize = struct.unpack_from("<BBH", val, 96 + 4 * x)
                            if xtype == 8:                        # data stream
                                size = struct.unpack_from("<Q", val, p)[0]
                            p += (xsize + 7) & ~7
                    self.inodes[obj] = (private, size, bsd_flags, mode)
                elif kind == 8:                                   # file extent
                    logical = struct.unpack_from("<Q", key, 8)[0]
                    length, block = struct.unpack_from("<QQ", val, 0)
                    self.extents.setdefault(obj, []).append((logical, length & ((1 << 56) - 1), block))
                elif kind == 4:                                   # extended attribute
                    nlen = struct.unpack_from("<H", key, 8)[0]
                    name = key[10:10 + nlen - 1].decode("utf-8", "replace")
                    flags, dlen = struct.unpack_from("<HH", val, 0)
                    self.xattrs.setdefault(obj, {})[name] = (flags, val[4:4 + dlen])
        walk(root_oid)

        root = Node("", "dir", 2)
        nodes[2] = root
        for parent, name, fid, dtype in dirents:
            kind = {4: "dir", 10: "link"}.get(dtype, "file")
            nodes.setdefault(fid, Node(name, kind, fid))
        for parent, name, fid, _t in dirents:
            if parent in nodes and fid in nodes:
                nodes[parent].children[name] = nodes[fid]
        self.root = root

    def _stream(self, sid: int, size: int) -> bytes:
        out = bytearray()
        for logical, length, block in sorted(self.extents.get(sid, [])):
            out = out.ljust(logical, b"\0")
            out[logical:] = self.dev.read(block * self.bs, length) if block else bytes(length)
        return bytes(out[:size].ljust(size, b"\0"))

    def _xattr(self, fid: int, name: str) -> bytes | None:
        entry = self.xattrs.get(fid, {}).get(name)
        if entry is None:
            return None
        flags, data = entry
        if flags & 2:                                             # embedded
            return data
        sid, size = struct.unpack_from("<QQ", data, 0)
        return self._stream(sid, size)

    def read_file(self, node: Node) -> bytes:
        if node.kind == "link":
            return (self._xattr(node.fid, "com.apple.fs.symlink") or b"").rstrip(b"\0")
        private, size, bsd_flags, _mode = self.inodes[node.fid]
        if bsd_flags & 0x20:
            header = self._xattr(node.fid, "com.apple.decmpfs")
            if header:
                return decmpfs(header, lambda: self._xattr(node.fid, "com.apple.ResourceFork") or b"")
        return self._stream(private, size)


# ── Disk image -> volume -> apps ──────────────────────────────────────

def open_volume(path: str) -> Volume:
    disk = Udif(path)
    starts = []
    for name, start in disk.partitions:
        starts.append(start)
        if "GUID_partition_scheme" in name or "Protective Master Boot Record" in name or start == 0:
            starts += _gpt_partitions(disk, start)
    errors = []
    for start in dict.fromkeys(starts):
        dev = Slice(disk, start)
        head = dev.read(0, 1100)
        try:
            if head[1024:1026] in (b"H+", b"HX"):
                return Hfs(dev)
            if head[32:36] == b"NXSB":
                return Apfs(dev)
        except (DmgError, struct.error, KeyError, IndexError, zlib.error, lzma.LZMAError, OSError) as e:
            errors.append(str(e))
    raise DmgError("no HFS+ or APFS volume found" + (": " + "; ".join(errors) if errors else ""))


def _gpt_partitions(disk: Udif, base: int) -> list[int]:
    head = disk.read(base + SECTOR, SECTOR)
    if head[:8] != b"EFI PART":
        return []
    lba, count, size = struct.unpack_from("<QII", head, 72)
    table = disk.read(base + lba * SECTOR, count * size)
    out = []
    for k in range(count):
        entry = table[k * size:(k + 1) * size]
        first = struct.unpack_from("<Q", entry, 32)[0]
        if entry[:16] != bytes(16):
            out.append(base + first * SECTOR)
    return out


def find_apps(volume: Volume, max_depth: int = 3) -> list[str]:
    """Bundle paths of the `.app`s, outermost first (an app's own helper
    apps inside Contents are left out)."""
    found = []

    def walk(node: Node, path: str, depth: int):
        for name, child in sorted(node.children.items()):
            if child.kind != "dir" or name.startswith("."):
                continue
            sub = f"{path}/{name}" if path else name
            if name.lower().endswith(".app"):
                found.append(sub)
            elif depth < max_depth:
                walk(child, sub, depth + 1)
    walk(volume.root, "", 0)
    return found


def info_plist(volume: Volume, bundle: str) -> dict:
    node = volume.lookup(bundle + "/Contents/Info.plist")
    if node is None:
        return {}
    try:
        return plistlib.loads(volume.read_file(node))
    except Exception:
        return {}


def app_name(volume: Volume, bundle: str) -> str:
    info = info_plist(volume, bundle)
    return str(info.get("CFBundleDisplayName") or info.get("CFBundleName")
               or PurePosixPath(bundle).stem)


def app_car(volume: Volume, bundle: str) -> tuple[bytes | None, str]:
    """The app's asset catalog (Contents/Resources/Assets.car) and the name
    of its icon there (CFBundleIconName)."""
    info = info_plist(volume, bundle)
    name = info.get("CFBundleIconName")
    node = volume.lookup(bundle + "/Contents/Resources/Assets.car")
    data = volume.read_file(node) if node is not None and node.kind == "file" else None
    return data, name if isinstance(name, str) else ""


def app_icon(volume: Volume, bundle: str) -> bytes:
    """The .icns of an app bundle."""
    info = info_plist(volume, bundle)
    resources = volume.lookup(bundle + "/Contents/Resources")
    names = []
    icon = info.get("CFBundleIconFile")
    if isinstance(icon, str) and icon:
        names += [icon, icon + ".icns"]
    icon_name = info.get("CFBundleIconName")
    if isinstance(icon_name, str) and icon_name:
        names.append(icon_name + ".icns")
    names += ["AppIcon.icns", "app.icns"]
    for name in names:
        node = volume.lookup(f"{bundle}/Contents/Resources/{name}")
        if node is not None and node.kind == "file":
            data = volume.read_file(node)
            if data[:4] == b"icns":
                return data
    if resources is not None:                       # the only .icns there
        icns = [c for n, c in resources.children.items() if n.lower().endswith(".icns")]
        if len(icns) == 1:
            data = volume.read_file(icns[0])
            if data[:4] == b"icns":
                return data
        if "Assets.car" in resources.children:
            raise DmgError("this app's icon is only in Assets.car")
    raise DmgError("no .icns icon in this app")


def main(argv: list[str]) -> int:
    try:
        if len(argv) == 2 and argv[0] == "list":
            volume = open_volume(argv[1])
            for bundle in find_apps(volume):
                print(f"{app_name(volume, bundle)}\t{bundle}")
            return 0
        if len(argv) == 4 and argv[0] == "extract":
            volume = open_volume(argv[1])
            data = app_icon(volume, argv[2])
            with open(argv[3], "wb") as out:
                out.write(data)
            return 0
    except (DmgError, OSError, struct.error, zlib.error, lzma.LZMAError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
