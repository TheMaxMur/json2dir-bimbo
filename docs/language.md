# bimbo-lang 0.1 — the bestie handbook 💅📚✨

This language has one practical job: implementing json2dir. The frontend
compiles your program into LLVM IR, then Clang builds the executable.
One mission, two braincells, zero interpreter energy. 🧠🎀

## Grammar: the guest list 📋💖

```ebnf
program   = { global | function } ;
global    = "glam" name ":" type "=" literal ";" ;
function  = "bestie" name "(" [ params ] ")" "->" return_type block ;
params    = name ":" type { "," name ":" type } ;
type      = "tea" | "yass" | "gloss" | "doll" ;
return_type = type | "ghost" ;
block     = "{" { statement } "}" ;
statement = "glam" name ":" type "=" expression ";"
          | name "=" expression ";"
          | "gimme" [ expression ] ";"
          | "vibecheck" expression block [ "whatever" ( block | statement_if ) ]
          | "strut" expression block
          | expression ";" ;
statement_if = "vibecheck" expression block [ "whatever" ( block | statement_if ) ] ;
```

Names start with an ASCII letter or `_`, followed by letters, digits, or `_`.
Keywords and type names are reserved. Comments start with `//` or `💅`.
Your gossip gets a whole line; your identifiers still need ID at the door. 🪪🚪

The entry point must be `bestie main() -> tea`. Its return value becomes
a 32-bit exit code. `argc()` includes the program name. Main character energy
is mandatory, bestie. 👑

## Types and expressions: pick an outfit 👗👜

- `tea` ☕ — a signed 64-bit integer. Decimal literals range from
  `-9223372036854775808` to `9223372036854775807`. `+`, `-`, `*`, and unary `-`
  wrap modulo 2^64. `/` truncates toward zero; `%` follows the dividend's sign.
  Division or remainder by zero is a runtime error. `INT64_MIN / -1` returns
  `INT64_MIN`, with remainder 0. Girl math has a written contract. 🧮
- `yass` ✅ — a boolean: `slay`, `flop`, `!`, `&&`, `||`. Both binary operators
  short circuit: the right side runs only when needed. No unnecessary drama. 💅
- `gloss` 💄 — UTF-8 bytes with an explicit length. Literals use JSON escapes
  (`\n`, `\uXXXX`, etc.) and may contain NUL. `+` concatenates strings;
  `==` and `!=` compare every byte. Indexing and length operate **in bytes**.
- `doll` 🪆 — an opaque pointer to a runtime container. Access it through
  builtin functions; `==` and `!=` compare object identity. Same purse, same doll.
- `ghost` 👻 — no value, valid only as a function's return type.
  Return with `gimme;` or reach the end of the body. Your ex could never.

There are no implicit type conversions. `< <= > >=` work only on `tea`;
`== !=` work on all value types when both operands have the same type.
The compiler checks the dress code before the party starts. 🚨👠

Precedence, lowest to highest: `||`, `&&`, `== !=`, `< <= > >=`, `+ -`,
`* / %`, then unary `! -`. Binary operators associate left to right. Function
arguments are evaluated left to right; parentheses change expression grouping.

## Variables and functions: meet the squad 👯‍♀️✨

All variables are mutable and require a type and initializer. Local variables
are visible within their block after declaration. An inner block may shadow an
outer name. Parameters and the outer function body share a scope. Global
variables are visible to every function and require a `tea`, `yass`, or `gloss`
literal initializer; global `doll` variables are unsupported.

Functions may call each other before declaration, including mutual recursion.
Overloading is unsupported. Every path out of a function returning a value
must have `gimme` or a direct `panic` call. A loop does not prove a return,
even with `strut slay`: such a function still needs a fallback return after
the loop. Statements immediately after a direct `gimme` or `panic` are rejected
as unreachable. Once she's left brunch, she's left brunch. 🥐🚕

```bimbo
bestie factorial(n: tea) -> tea {
    vibecheck n <= 1 { gimme 1; }
    whatever { gimme n * factorial(n - 1); }
}

bestie main() -> tea {
    spill("girl math 🧮💅: " + caption(factorial(5)) + " — academically slaying ✨");
    gimme 0;
}
```

## Builtins: what's in the purse? 👜💄🔧

Below, `ghost` means no return value. Using the wrong container kind or an
out-of-bounds index causes a runtime error with exit code 1.
The purse is spacious, bestie, but it is not a wormhole. 🕳️🚫

| Function | Returns | Action |
|---|---|---|
| `spill(gloss)` ☕ | ghost | print to stdout with a newline |
| `panic(gloss)` 😱 | ghost | print `Error: ...` to stderr and exit with code 1 |
| `argc()` 🎟️ | tea | argument count, including the program name |
| `sip()` 🧋 | gloss | read all stdin; reject read errors and invalid UTF-8 |
| `length(gloss)` 📏 | tea | byte length |
| `byte(gloss, tea)` 🔎 | tea | byte 0…255 at an index |
| `slice(gloss, tea, tea)` ✂️ | gloss | range `[start, end)` |
| `caption(tea)` 💬 | gloss | decimal integer representation |
| `affordable(tea, tea, tea)` 💸 | yass | whether `(high * 10^9 + low)`, rounded to double then scaled by `10^exponent`, remains finite |
| `lipstick()` 💄 | doll | empty byte buffer, kind 4 |
| `dab(doll, tea)` 🖌️ | ghost | append a byte 0…255 to a buffer |
| `sparkle(doll, tea)` ✨ | ghost | append a Unicode scalar as UTF-8 |
| `reveal(doll)` 🎁 | gloss | immutable copy of a buffer's contents |
| `closet()` 👗 | doll | empty ordered map, kind 1 |
| `accessory(gloss)` 🎀 | doll | string object, kind 2 |
| `squad()` 👯 | doll | empty vector, kind 3 |
| `basic()` 🫠 | doll | opaque scalar value, kind 0 |
| `kind(doll)` 🪪 | tea | kind number |
| `size(doll)` 🛍️ | tea | number of entries in a map, vector, or buffer |
| `dress(doll, gloss, doll)` 👚 | ghost | insert into a map; replace a duplicate key |
| `invite(doll, doll)` 💌 | ghost | append to a vector |
| `guest(doll, tea)` 🥂 | doll | map or vector value at an index |
| `label(doll, tea)` 🏷️ | gloss | map key at an index, sorted by UTF-8 bytes |
| `outfit(doll)` 👠 | gloss | string object's value |
| `unfollow(gloss)` 💔 | ghost | `unlink`; ignore removal errors |
| `penthouse(gloss)` 🏰 | ghost | `mkdir(0777)` with umask; allow EEXIST |
| `catwalk(gloss)` 🚶‍♀️ | ghost | `chdir` into a directory |
| `backstage(gloss)` 🎭 | ghost | `chdir("..")`; argument supplies error context |
| `diary(gloss, gloss)` 📓 | ghost | create/overwrite a file with exact bytes |
| `heels(gloss)` 👠 | ghost | add execute bits `0111` to current permissions |
| `situationship(gloss, gloss)` 🔗 | ghost | create a symlink: path, target |

Maps compare keys by bytes, with explicit lengths and support for NUL.
Filesystem paths and symlink targets containing NUL are rejected. Filesystem
paths resolve relative to the process's cwd, so json2dir can enter directories
without building a long full path for every syscall.

The json2dir parser uses `basic()` to represent valid JSON numbers, booleans,
and null, which the filesystem schema rejects. Their values are not retained.
Valid JSON, invalid outfit. A tragic but well-typed evening. 🫠👗

`affordable` takes two nonnegative limbs for a u64 significand:
`low < 10^9`, with the combined value at most `UINT64_MAX`. A negative exponent
cannot overflow double and may underflow to zero. Number syntax, significand
accumulation, discarded digits, and exponent validation are implemented in
`.bimbo`. This preserves the original project's default `serde_json` rounding
order. Even the budget has compatibility requirements. 💸🧮

## Lifetimes: the afterparty cleanup 🧹🪩

Strings and containers live until the process exits. Buffers and containers
grow geometrically; earlier allocations stay in the arena. The arena is freed
on exit, including `panic` and POSIX errors. `slice` shares storage with its
source string; `reveal` makes a copy unaffected by later `dab` calls.

This approach suits a short CLI program that reads one JSON document.
Version 0.1 has no modules, user-defined structs or pointers, classes,
exceptions, break, continue, threads, or garbage collector.
We booked one brunch, bestie. We did not open a distributed nightclub. 🥐💅
