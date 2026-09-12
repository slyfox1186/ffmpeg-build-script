"""A byte-compatible reimplementation of Bash's `printf '%q'`.

The build-context record encodes seven fields this way, and every workspace
created by an earlier release of this project holds those bytes. Encoding them
any other way — `shlex.quote` produces `'-O2 -pipe'` where Bash produces
`-O2\\ -pipe` — would make every existing workspace compare unequal, and users
would be told to run `--cleanup` for a change that never happened.

The rules below were derived by enumerating every byte through
`printf '%q'` under `LC_ALL=C`, which is the locale the build exports before
the record is written.
"""

from __future__ import annotations

# Printable characters Bash prefixes with a backslash. Everything else in the
# printable ASCII range, including `% + - . / : = @ _`, is emitted verbatim.
_BACKSLASH_ESCAPED = frozenset(" !\"$&'()*,;<>?[\\]^`{|}")

# `#` starts a comment only in the first position of a word. `~` starts an
# expansion in that position and also directly after `:` or `=`, which is what
# makes `PATH=a:~/bin` expand; Bash escapes it in exactly those three places.
_TILDE_EXPANSION_PREDECESSORS = frozenset(":=")

# Control characters with a named ANSI-C escape; every other non-printable byte
# becomes a three-digit octal escape.
_NAMED_ESCAPES = {
    0x07: "\\a",
    0x08: "\\b",
    0x09: "\\t",
    0x0A: "\\n",
    0x0B: "\\v",
    0x0C: "\\f",
    0x0D: "\\r",
    0x1B: "\\E",
}
_NAMED_UNESCAPES = {
    "a": "\x07",
    "b": "\x08",
    "t": "\x09",
    "n": "\x0a",
    "v": "\x0b",
    "f": "\x0c",
    "r": "\x0d",
    "E": "\x1b",
    "e": "\x1b",
    "\\": "\\",
    "'": "'",
    '"': '"',
}


def _needs_ansi_c(value: str) -> bool:
    return any(ord(character) < 0x20 or ord(character) >= 0x7F for character in value)


def _ansi_c_quote(value: str) -> str:
    rendered = ["$'"]
    for byte in value.encode("utf-8", "surrogateescape"):
        if byte in _NAMED_ESCAPES:
            rendered.append(_NAMED_ESCAPES[byte])
        elif byte < 0x20 or byte >= 0x7F:
            rendered.append(f"\\{byte:03o}")
        elif byte in (0x27, 0x5C):
            rendered.append("\\" + chr(byte))
        else:
            rendered.append(chr(byte))
    rendered.append("'")
    return "".join(rendered)


def quote(value: str) -> str:
    """Encode one word exactly as `printf '%q'` would."""
    if not value:
        return "''"
    if _needs_ansi_c(value):
        return _ansi_c_quote(value)
    rendered: list[str] = []
    for position, character in enumerate(value):
        if character in _BACKSLASH_ESCAPED:
            escape = True
        elif character == "#":
            escape = position == 0
        elif character == "~":
            escape = position == 0 or value[position - 1] in _TILDE_EXPANSION_PREDECESSORS
        else:
            escape = False
        rendered.append(f"\\{character}" if escape else character)
    return "".join(rendered)


def join(arguments: list[str] | tuple[str, ...]) -> str:
    """Render an argument list the way the build logs a command."""
    return " ".join(quote(argument) for argument in arguments)


def _unquote_ansi_c(value: str) -> str:
    body = value[2:-1]
    out = bytearray()
    index = 0
    while index < len(body):
        character = body[index]
        if character != "\\":
            out.extend(character.encode("utf-8", "surrogateescape"))
            index += 1
            continue
        index += 1
        if index >= len(body):
            out.append(ord("\\"))
            break
        escape = body[index]
        if escape in _NAMED_UNESCAPES:
            out.extend(_NAMED_UNESCAPES[escape].encode("utf-8"))
            index += 1
        elif escape.isdigit():
            digits = ""
            while index < len(body) and len(digits) < 3 and body[index] in "01234567":
                digits += body[index]
                index += 1
            out.append(int(digits, 8) & 0xFF)
        else:
            out.extend(escape.encode("utf-8", "surrogateescape"))
            index += 1
    return out.decode("utf-8", "surrogateescape")


def unquote(value: str) -> str:
    """Decode a value produced by `quote`.

    Required to read back records written by any release of this project, so
    the parser is part of the format contract rather than a convenience.
    """
    if value in ("", "''"):
        return ""
    if value.startswith("$'") and value.endswith("'") and len(value) >= 3:
        return _unquote_ansi_c(value)
    out: list[str] = []
    index = 0
    while index < len(value):
        character = value[index]
        if character == "\\" and index + 1 < len(value):
            out.append(value[index + 1])
            index += 2
            continue
        out.append(character)
        index += 1
    return "".join(out)


def readable(value: str) -> str:
    """Render an encoded value the way the shell would actually run it.

    The encoding turns a flag list into backslash noise for a reader, so the
    mismatch message undoes it. The `$'...'` form is shown verbatim: its escapes
    are not single-character pairs, and mangling one would be worse than leaving
    it encoded.
    """
    if value in ("", "''"):
        return "''"
    if value.startswith("$'"):
        return value
    return f"'{unquote(value)}'"
