# bimbo-lang 💅🎀✨

**No thoughts. Just LLVM.**

📺 [YouTube: @kindashasha](https://www.youtube.com/@kindashasha) · 💌 [Telegram: @swagshasha](https://t.me/swagshasha)

Statically typed. Emotionally unavailable. Ahead-of-time fabulous. 💄🧠👠

A tiny compiled language that took its LLVM course at a nail salon.
Built for exactly one mission: rewriting [alurm/json2dir](https://github.com/alurm/json2dir). It has static types,
recursion, short circuit evaluation, and an emotional depth of 127 containers.
At the 128th, it asks you to discuss this with your therapist. 🛋️💀

```bimbo
💅🎀 Girl math, with proper control flow. The loops have runway experience. 👠
bestie main() -> tea {
    glam braincells: tea = 2;
    strut braincells > 0 {
        spill("🧠 bestie, I have " + caption(braincells) + " braincells and both emit LLVM 💅✨");
        braincells = braincells - 1;
    }
    vibecheck braincells == 0 {
        spill("no thoughts, just native code 💅🎀✨");
    }
    gimme 0;
}
```

## Let's go, bestie 🚀💖

Requires Python 3.10+ and Clang 15+ with LLVM IR support. No Python dependencies.
The runtime uses POSIX; the project targets macOS and Linux with 64-bit pointers.
Tested on macOS arm64 with Apple Clang 21 and Python 3.14.

```sh
make
./bimbo run examples/hello.bimbo
make demo
```

`make` creates the **native binary** `build/json2dir` and LLVM IR
`build/json2dir.ll`. Running the binary does not require Python.

Turn JSON into files in a separate directory:

```sh
mkdir -p build/my-closet
(cd build/my-closet && ../json2dir < ../../examples/closet.json && ./slay.sh)
```

The binary reads JSON from stdin and accepts no arguments, just like the original json2dir:

```sh
/path/to/json2dir-bimbo/build/json2dir < file.json
```

Files are created in the process's **current directory**. New closet, who dis? 📁👗

## The bestie dictionary 📖💋

| Syntax | Meaning | Lore |
|---|---|---|
| `bestie` | function | the friend who actually gets things done 👯‍♀️ |
| `glam` | mutable variable | every variable needs an outfit 👗 |
| `vibecheck` / `whatever` | if / else | pass the vibecheck, or whatever 🙄✨ |
| `strut` | while | walk the runway while the condition holds 👠 |
| `gimme` | return | hand over the result, bestie 🫴💖 |
| `slay` / `flop` | true / false | the project's two moods 👑💀 |
| `tea` | signed i64 | strictly integer tea ☕🧮 |
| `yass` | bool | a confident yes, or a flop ✅🫠 |
| `gloss` | string with an explicit byte length | UTF-8 shine, with room for embedded NUL 💄 |
| `doll` | opaque container | a purse for objects, arrays, and buffers 👜 |
| `ghost` | void | returns nothing, just like your ex 👻💔 |
| `💅` or `//` | line comment | the compiler patiently listens to your gossip ☕👀 |

See the full [language specification and builtin reference](docs/language.md).

## Where's json2dir? In the walk-in closet 📁👗

**The entire JSON parser and directory creation algorithm live in
[`src/json2dir.bimbo`](src/json2dir.bimbo).**

It supports the same conversion scheme as the original Rust project in `../json2dir`:

| JSON | Result |
|---|---|
| `{"room": {}}` | directory `room` |
| `{"diary": "text"}` | file `diary` containing exactly `text` |
| `{"ex": ["link", "target"]}` | symlink `ex` → `target` |
| `{"slay": ["script", "#!/bin/sh\n..."]}` | file `slay` with execute bits `0111` added |

The original's behavioral details are preserved:

- The root must be an object; numbers, booleans, and null do not describe files.
- The entire JSON document is parsed before files are changed. UTF-8, escapes,
  and Unicode surrogate pairs are validated; file contents may contain NUL.
- Duplicate keys replace earlier values. Keys are visited in sorted order,
  matching the default `serde_json::Map` without `preserve_order`.
- Existing files and symlinks are removed before processing their values.
  Existing directories are merged, retain older entries, and are never
  recursively deleted to make room for a replacement.
- New files and directories respect umask; scripts get all three execute bits.
  Replacing a symlink normally leaves its former target's contents intact.
- Name validation mirrors Unix `Path::components`: empty names, `.`, `..`,
  absolute paths, and paths with multiple components are rejected. One original
  quirk: `foo/./` passes component validation, with ordinary POSIX operations
  determining whether creation succeeds.
- JSON is limited to 127 nested objects/arrays. Extra arguments fail with Usage.
- Success: exit code 0 and empty stdout. Failure: exit code 1, context on stderr,
  and a sprinkle of drama. 💔💅

Like the original, writes are not transactional: a **schema** error or failed
filesystem operation can leave a partial tree. An old file is removed before
its JSON value is validated. Concurrent filesystem changes are not protected
against TOCTOU races.

## How it's built: serving looks, lowering loops 🛠️👠

```text
.bimbo → lexer → parser → AST → type checking → LLVM IR (.ll)
                                                     ↓
                              Clang/LLVM + glitter.c → native binary
```

- [`compiler/bimboc.py`](compiler/bimboc.py) is a Python frontend that directly
  emits [LLVM IR](https://llvm.org/docs/LangRef.html). Functions, arithmetic,
  conditions, loops, and short circuit evaluation become LLVM instructions.
- [`runtime/glitter.c`](runtime/glitter.c) provides strings, an ordered map,
  a vector, a buffer, stdin reading, UTF-8 validation, and POSIX primitives.
  JSON parsing and directory traversal live in `.bimbo`. Programs are compiled
  ahead of time.
- Runtime objects live in an arena until the process exits; memory is freed
  on both normal completion and errors. No garbage collector or eternal server.

```sh
./bimbo check src/json2dir.bimbo
./bimbo emit src/json2dir.bimbo -o build/json2dir.ll
./bimbo build src/json2dir.bimbo -o build/json2dir -O 2
./bimbo build src/json2dir.bimbo --sanitize -O 1 -o build/json2dir-sanitize
```

Choose Clang with `--clang /path/to/clang` or the `CLANG` environment variable.
Compiler errors include the file, line, column, and a `^` pointer:
`expected tea, got yass; wrong outfit, bestie 💅🚨`.

## Tests: receipts or it didn't happen 🧾🔬✨

```sh
make test
make sanitize
```

Tests cover native code at `-O0` and `-O2`, type checking, scopes, recursion,
short circuit evaluation, JSON, Unicode, permissions, file replacement,
existing directories, depth limits, and randomly generated trees.
`make sanitize` runs json2dir with AddressSanitizer and UndefinedBehaviorSanitizer.

To compare against the Rust original, build its binary:

```sh
cargo build --offline --manifest-path ../json2dir/Cargo.toml --target-dir /tmp/bimbo-json2dir-reference
JSON2DIR_REFERENCE=/tmp/bimbo-json2dir-reference/debug/json2dir make test
JSON2DIR_REFERENCE=/tmp/bimbo-json2dir-reference/debug/json2dir make sanitize
```

Without `JSON2DIR_REFERENCE`, the six differential tests are skipped; regular
tests still run. Comparisons check exit codes, stdout, directory trees, exact
file bytes, symlink targets, and permissions. Error messages have their own flair.
The verifier saw the receipts and said yass. ✅💅

## Compiler catchphrases: put these on a tiny pink laptop 💻🎀

- **Relationship status: linked successfully.** 🔗💌
- **My love language is an opaque pointer.** 🫶👉
- **Girl math, verifier approved.** 🧮✅
- **I put the IR in girl.** 💄🧾
- **AOT: Ahead Of Therapy.** 🛋️✨
- **Serving looks, lowering loops.** 👠🔁

## Philosophy: two braincells, one mission 🧠🎀

The language is deliberately tiny: no classes, package manager, async, generics,
or self-hosting. We have two braincells: one parses JSON, the other creates
directories. If this project needs a third, that's bimbo-lang enterprise edition. 💸💀

The algorithm is adapted from json2dir by Alan Urmancheev; attribution is
preserved in [LICENSE](LICENSE).
