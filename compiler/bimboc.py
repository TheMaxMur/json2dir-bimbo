#!/usr/bin/env python3
"""bimbo-lang: a small, statically typed compiler that emits LLVM IR directly."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
TYPES = {"tea": "i64", "yass": "i1", "gloss": "ptr", "doll": "ptr", "ghost": "void"}
# The runtime provides containers and POSIX primitives, never JSON parsing or traversal.
BUILTINS = {
    "spill": ("ghost", ["gloss"]), "panic": ("ghost", ["gloss"]),
    "argc": ("tea", []), "sip": ("gloss", []),
    "length": ("tea", ["gloss"]), "byte": ("tea", ["gloss", "tea"]),
    "slice": ("gloss", ["gloss", "tea", "tea"]), "caption": ("gloss", ["tea"]),
    "affordable": ("yass", ["tea", "tea", "tea"]),
    "lipstick": ("doll", []), "dab": ("ghost", ["doll", "tea"]),
    "sparkle": ("ghost", ["doll", "tea"]), "reveal": ("gloss", ["doll"]),
    "closet": ("doll", []), "squad": ("doll", []), "accessory": ("doll", ["gloss"]),
    "basic": ("doll", []), "kind": ("tea", ["doll"]), "size": ("tea", ["doll"]),
    "invite": ("ghost", ["doll", "doll"]), "dress": ("ghost", ["doll", "gloss", "doll"]),
    "guest": ("doll", ["doll", "tea"]), "label": ("gloss", ["doll", "tea"]),
    "outfit": ("gloss", ["doll"]),
    "unfollow": ("ghost", ["gloss"]), "penthouse": ("ghost", ["gloss"]),
    "catwalk": ("ghost", ["gloss"]), "backstage": ("ghost", ["gloss"]),
    "diary": ("ghost", ["gloss", "gloss"]), "heels": ("ghost", ["gloss"]),
    "situationship": ("ghost", ["gloss", "gloss"]),
}


@dataclass
class Token:
    kind: str
    value: object
    line: int
    column: int


class CompileError(Exception):
    def __init__(self, token: Token, message: str):
        self.token, self.message = token, message


@dataclass
class Node:
    tag: str
    token: Token
    parts: tuple = ()


def lex(source: str) -> list[Token]:
    tokens, i, line, column = [], 0, 1, 1
    while i < len(source):
        c = source[i]
        if c.isspace():
            if c == "\n":
                line, column = line + 1, 1
            else:
                column += 1
            i += 1
            continue
        if source.startswith("//", i) or c == "💅":
            end = source.find("\n", i)
            if end == -1:
                break
            column += end - i
            i = end
            continue
        start, start_column = i, column
        if c == '"':
            i += 1
            while i < len(source) and source[i] != '"':
                if source[i] in "\r\n":
                    raise CompileError(Token("string", "", line, start_column), "string needs a closing quote, bestie")
                if source[i] == "\\":
                    i += 1
                i += 1
            if i >= len(source):
                raise CompileError(Token("string", "", line, start_column), "unterminated gloss; the tea has spilled")
            i += 1
            try:
                value = json.loads(source[start:i])
                value.encode("utf-8")
            except (ValueError, UnicodeError):
                raise CompileError(Token("string", "", line, start_column), "invalid string escape or Unicode") from None
            tokens.append(Token("string", value, line, start_column))
        elif c.isascii() and (c.isalpha() or c == "_"):
            i += 1
            while i < len(source) and source[i].isascii() and (source[i].isalnum() or source[i] == "_"):
                i += 1
            tokens.append(Token("name", source[start:i], line, start_column))
        elif c.isascii() and c.isdigit():
            i += 1
            while i < len(source) and source[i].isascii() and source[i].isdigit():
                i += 1
            digits = source[start:i].lstrip("0") or "0"
            if len(digits) > 19:
                raise CompileError(Token("number", "", line, start_column), "tea overflow: signed 64-bit integers only")
            tokens.append(Token("number", int(digits), line, start_column))
        elif source[i:i + 2] in ("->", "==", "!=", "<=", ">=", "&&", "||"):
            i += 2
            tokens.append(Token("symbol", source[start:i], line, start_column))
        elif c in "(){}:;,+-*/%<>=!":
            i += 1
            tokens.append(Token("symbol", c, line, start_column))
        else:
            raise CompileError(Token("symbol", c, line, column), f"unexpected {c!r}; this character is not on the guest list")
        column += i - start
    tokens.append(Token("eof", "<end>", line, column))
    return tokens


class Parser:
    PRECEDENCE = {"||": 1, "&&": 2, "==": 3, "!=": 3, "<": 4, "<=": 4, ">": 4, ">=": 4,
                  "+": 5, "-": 5, "*": 6, "/": 6, "%": 6}

    def __init__(self, source: str):
        self.tokens, self.pos = lex(source), 0

    def peek(self) -> Token:
        return self.tokens[self.pos]

    def take(self) -> Token:
        token = self.peek()
        self.pos += 1
        return token

    def accept(self, value: str) -> bool:
        if self.peek().kind in ("name", "symbol") and self.peek().value == value:
            self.take()
            return True
        return False

    def expect(self, value: str) -> Token:
        if self.peek().kind not in ("name", "symbol") or self.peek().value != value:
            raise CompileError(self.peek(), f"expected {value!r}, got {self.peek().value!r}; vibecheck failed")
        return self.take()

    def name(self) -> Token:
        t = self.take()
        reserved = {"bestie", "glam", "gimme", "vibecheck", "whatever", "strut", "slay", "flop"} | TYPES.keys()
        if t.kind != "name" or t.value in reserved:
            raise CompileError(t, "expected a name for this bestie")
        return t

    def type_name(self, allow_void: bool = False) -> str:
        t = self.take()
        if t.value not in TYPES or (t.value == "ghost" and not allow_void):
            raise CompileError(t, "expected tea, yass, gloss or doll" + (" (or ghost)" if allow_void else ""))
        return str(t.value)

    def variable(self) -> Node:
        token = self.expect("glam")
        name = self.name().value
        self.expect(":")
        typ = self.type_name()
        self.expect("=")
        value = self.expression()
        self.expect(";")
        return Node("var", token, (name, typ, value))

    def program(self) -> list[Node]:
        result = []
        while self.peek().kind != "eof":
            if self.peek().value == "glam":
                result.append(self.variable())
                continue
            token = self.expect("bestie")
            name = self.name().value
            self.expect("(")
            params = []
            if not self.accept(")"):
                while True:
                    p = self.name()
                    self.expect(":")
                    params.append((p, self.type_name()))
                    if self.accept(")"):
                        break
                    self.expect(",")
            self.expect("->")
            typ = self.type_name(True)
            result.append(Node("fn", token, (name, params, typ, self.block())))
        return result

    def block(self) -> list[Node]:
        self.expect("{")
        statements = []
        while not self.accept("}"):
            if self.peek().kind == "eof":
                raise CompileError(self.peek(), "missing closing }; wardrobe malfunction")
            statements.append(self.statement())
        return statements

    def statement(self) -> Node:
        t = self.peek()
        if t.kind == "name" and t.value == "glam":
            return self.variable()
        if self.accept("gimme"):
            e = None if self.peek().value == ";" else self.expression()
            self.expect(";")
            return Node("return", t, (e,))
        if self.accept("vibecheck"):
            condition = self.expression()
            yes = self.block()
            no = []
            if self.accept("whatever"):
                no = [self.statement()] if self.peek().value == "vibecheck" else self.block()
            return Node("if", t, (condition, yes, no))
        if self.accept("strut"):
            return Node("while", t, (self.expression(), self.block()))
        if t.kind == "name" and self.tokens[self.pos + 1].value == "=":
            self.take()
            self.take()
            e = self.expression()
            self.expect(";")
            return Node("assign", t, (t.value, e))
        e = self.expression()
        self.expect(";")
        return Node("expr", t, (e,))

    def expression(self, minimum: int = 0) -> Node:
        t = self.take()
        if t.kind == "symbol" and t.value in ("!", "-"):
            left = Node("unary", t, (str(t.value), self.expression(7)))
        elif t.kind == "symbol" and t.value == "(":
            left = self.expression()
            self.expect(")")
        elif t.kind == "number":
            left = Node("number", t, (t.value,))
        elif t.kind == "string":
            left = Node("string", t, (t.value,))
        elif t.kind == "name" and t.value in ("slay", "flop"):
            left = Node("bool", t, (t.value == "slay",))
        elif t.kind == "name":
            if self.accept("("):
                args = []
                if not self.accept(")"):
                    while True:
                        args.append(self.expression())
                        if self.accept(")"):
                            break
                        self.expect(",")
                left = Node("call", t, (t.value, args))
            else:
                left = Node("name", t, (t.value,))
        else:
            raise CompileError(t, "expected an expression; no thoughts, head empty")
        while self.peek().kind == "symbol" and (precedence := self.PRECEDENCE.get(self.peek().value, -1)) >= minimum:
            op = self.take()
            right = self.expression(precedence + 1)
            left = Node("binary", op, (op.value, left, right))
        return left


class Compiler:
    def __init__(self, nodes: list[Node], source_name: str):
        self.nodes, self.source_name = nodes, source_name
        self.functions = dict(BUILTINS)
        self.globals: dict[str, tuple[str, str]] = {}
        self.constants: list[str] = []
        self.strings: dict[str, str] = {}
        self.global_lines: list[str] = []

    def string(self, value: str) -> str:
        if value not in self.strings:
            raw = value.encode("utf-8")
            index = len(self.strings)
            data, obj = f"@.bytes{index}", f"@.gloss{index}"
            encoded = "".join(f"\\{b:02X}" for b in raw) + "\\00"
            self.constants.append(f'{data} = private unnamed_addr constant [{len(raw) + 1} x i8] c"{encoded}"')
            self.constants.append(f"{obj} = private constant {{ i64, ptr }} {{ i64 {len(raw)}, ptr {data} }}")
            self.strings[value] = obj
        return self.strings[value]

    @staticmethod
    def integer(node: Node) -> str:
        value = node.parts[0]
        if not -(2**63) <= value < 2**63:
            raise CompileError(node.token, "tea overflow: signed 64-bit integers only")
        return str(value)

    def compile(self) -> str:
        seen = set(BUILTINS)
        for node in self.nodes:
            name = node.parts[0]
            if name in seen:
                raise CompileError(node.token, f"{name!r} is already on the guest list")
            seen.add(name)
            if node.tag == "fn":
                _, params, ret, _ = node.parts
                self.functions[name] = (ret, [typ for _, typ in params])
            else:
                _, typ, e = node.parts
                if e.tag == "unary" and e.parts[0] == "-" and e.parts[1].tag == "number":
                    e = Node("number", e.token, (-e.parts[1].parts[0],))
                expected = {"number": "tea", "string": "gloss", "bool": "yass"}.get(e.tag)
                if expected != typ:
                    raise CompileError(e.token, "global glam needs a literal of its declared type")
                value = self.integer(e) if typ == "tea" else self.string(e.parts[0]) if typ == "gloss" else str(int(e.parts[0]))
                ptr = f"@bimbo_global_{name}"
                self.globals[name] = (typ, ptr)
                self.global_lines.append(f"{ptr} = internal global {TYPES[typ]} {value}")
        if self.functions.get("main") != ("tea", []) or "main" in BUILTINS:
            raise CompileError(Token("name", "main", 1, 1), "give me bestie main() -> tea { ... }")
        bodies = [FunctionCompiler(self, n).compile() for n in self.nodes if n.tag == "fn"]
        declarations = [f"declare {TYPES[ret]} @bimbo_{name}({', '.join(TYPES[t] for t in args)})" for name, (ret, args) in BUILTINS.items()]
        declarations += ["declare ptr @bimbo_concat(ptr, ptr)", "declare i1 @bimbo_equal(ptr, ptr)",
                         "declare i64 @bimbo_divide(i64, i64)", "declare i64 @bimbo_modulo(i64, i64)",
                         "declare void @bimbo_init(i32)", "declare void @bimbo_shutdown()"]
        wrapper = """define i32 @main(i32 %argc, ptr %argv) {
entry:
  call void @bimbo_init(i32 %argc)
  %result = call i64 @bimbo_fn_main()
  call void @bimbo_shutdown()
  %status = trunc i64 %result to i32
  ret i32 %status
}"""
        return "\n\n".join(["; bimbo-lang: LLVM, but make it pink.\n; Source: " + json.dumps(self.source_name),
                              "\n".join(self.constants), "\n".join(self.global_lines),
                              "\n".join(declarations), *bodies, wrapper]) + "\n"


class FunctionCompiler:
    def __init__(self, compiler: Compiler, node: Node):
        self.compiler, self.node = compiler, node
        self.name, self.params, self.ret, self.statements = node.parts
        self.code: list[str] = []
        self.allocas: list[str] = []
        self.scopes: list[dict[str, tuple[str, str]]] = [{}]
        self.count, self.current, self.terminated = 0, "entry", False

    def fresh(self, prefix: str = "v") -> str:
        self.count += 1
        return f"{prefix}{self.count}"

    def emit(self, line: str):
        self.code.append("  " + line)

    def value(self, instruction: str) -> str:
        result = "%" + self.fresh()
        self.emit(f"{result} = {instruction}")
        return result

    def mark(self, label: str):
        self.code.append(label + ":")
        self.current, self.terminated = label, False

    def branch(self, label: str):
        self.emit(f"br label %{label}")
        self.terminated = True

    def variable(self, name: str, token: Token) -> tuple[str, str]:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        if name in self.compiler.globals:
            return self.compiler.globals[name]
        raise CompileError(token, f"who is {name!r}? declare her with glam first")

    def bind(self, name: str, typ: str, token: Token) -> str:
        if name in self.scopes[-1]:
            raise CompileError(token, f"{name!r} already has an outfit in this scope")
        ptr = "%" + self.fresh("slot")
        self.allocas.append(f"  {ptr} = alloca {TYPES[typ]}")
        self.scopes[-1][name] = (typ, ptr)
        return ptr

    @staticmethod
    def require(actual: str, expected: str, token: Token):
        if actual != expected:
            raise CompileError(token, f"expected {expected}, got {actual}; wrong outfit, bestie")

    def expression(self, e: Node) -> tuple[str, str]:
        tag, p = e.tag, e.parts
        if tag == "number":
            return "tea", self.compiler.integer(e)
        if tag == "string":
            return "gloss", self.compiler.string(p[0])
        if tag == "bool":
            return "yass", str(int(p[0]))
        if tag == "name":
            typ, ptr = self.variable(p[0], e.token)
            return typ, self.value(f"load {TYPES[typ]}, ptr {ptr}")
        if tag == "call":
            name, args = p
            if name not in self.compiler.functions:
                raise CompileError(e.token, f"unknown bestie {name!r}")
            ret, types = self.compiler.functions[name]
            if len(args) != len(types):
                raise CompileError(e.token, f"{name} wants {len(types)} arguments, got {len(args)}")
            values = []
            for arg, expected in zip(args, types):
                typ, value = self.expression(arg)
                self.require(typ, expected, arg.token)
                values.append(f"{TYPES[typ]} {value}")
            symbol = f"bimbo_{name}" if name in BUILTINS else f"bimbo_fn_{name}"
            call = f"call {TYPES[ret]} @{symbol}({', '.join(values)})"
            if ret == "ghost":
                self.emit(call)
                return ret, ""
            return ret, self.value(call)
        if tag == "unary":
            op, arg = p
            if op == "-" and arg.tag == "number":
                return "tea", self.compiler.integer(Node("number", e.token, (-arg.parts[0],)))
            typ, val = self.expression(arg)
            self.require(typ, "yass" if op == "!" else "tea", e.token)
            return typ, self.value(f"xor i1 {val}, true" if op == "!" else f"sub i64 0, {val}")
        op, a, b = p
        ta, va = self.expression(a)
        if op in ("&&", "||"):
            self.require(ta, "yass", e.token)
            origin, rhs, end = self.current, self.fresh("rhs"), self.fresh("join")
            self.emit(f"br i1 {va}, label %{rhs if op == '&&' else end}, label %{end if op == '&&' else rhs}")
            self.mark(rhs)
            tb, vb = self.expression(b)
            self.require(tb, "yass", b.token)
            rhs_end = self.current
            self.branch(end)
            self.mark(end)
            val = "0" if op == "&&" else "1"
            return "yass", self.value(f"phi i1 [ {val}, %{origin} ], [ {vb}, %{rhs_end} ]")
        tb, vb = self.expression(b)
        self.require(tb, ta, b.token)
        if op == "+" and ta == "gloss":
            return "gloss", self.value(f"call ptr @bimbo_concat(ptr {va}, ptr {vb})")
        if op in ("==", "!="):
            if ta == "gloss":
                equal = self.value(f"call i1 @bimbo_equal(ptr {va}, ptr {vb})")
                return "yass", equal if op == "==" else self.value(f"xor i1 {equal}, true")
            if ta not in ("tea", "yass", "doll"):
                raise CompileError(e.token, "ghosts cannot be compared")
            return "yass", self.value(f"icmp {'eq' if op == '==' else 'ne'} {TYPES[ta]} {va}, {vb}")
        self.require(ta, "tea", e.token)
        if op in ("<", "<=", ">", ">="):
            pred = {"<": "slt", "<=": "sle", ">": "sgt", ">=": "sge"}[op]
            return "yass", self.value(f"icmp {pred} i64 {va}, {vb}")
        if op in ("/", "%"):
            return "tea", self.value(f"call i64 @bimbo_{'divide' if op == '/' else 'modulo'}(i64 {va}, i64 {vb})")
        instruction = {"+": "add", "-": "sub", "*": "mul"}[op]
        return "tea", self.value(f"{instruction} i64 {va}, {vb}")

    def block(self, statements: list[Node]):
        self.scopes.append({})
        for stmt in statements:
            if self.terminated:
                raise CompileError(stmt.token, "unreachable statement; she's already left the party")
            self.statement(stmt)
        self.scopes.pop()

    def statement(self, s: Node):
        p = s.parts
        if s.tag in ("var", "assign"):
            if s.tag == "var":
                name, typ, e = p
                actual, value = self.expression(e)
                self.require(actual, typ, e.token)
                ptr = self.bind(name, typ, s.token)
            else:
                name, e = p
                typ, ptr = self.variable(name, s.token)
                actual, value = self.expression(e)
                self.require(actual, typ, e.token)
            self.emit(f"store {TYPES[typ]} {value}, ptr {ptr}")
        elif s.tag == "return":
            e = p[0]
            if e is None:
                self.require(self.ret, "ghost", s.token)
                self.emit("ret void")
            else:
                typ, value = self.expression(e)
                self.require(typ, self.ret, e.token)
                if typ == "ghost":
                    raise CompileError(e.token, "use gimme; to return from a ghost bestie")
                self.emit(f"ret {TYPES[typ]} {value}")
            self.terminated = True
        elif s.tag == "expr":
            self.expression(p[0])
            if p[0].tag == "call" and p[0].parts[0] == "panic":
                self.emit("unreachable")
                self.terminated = True
        elif s.tag == "if":
            e, yes, no = p
            typ, val = self.expression(e)
            self.require(typ, "yass", e.token)
            a, b, end = self.fresh("yes"), self.fresh("no"), self.fresh("end")
            self.emit(f"br i1 {val}, label %{a}, label %{b}")
            self.mark(a)
            self.block(yes)
            yes_done = self.terminated
            if not yes_done:
                self.branch(end)
            self.mark(b)
            self.block(no)
            no_done = self.terminated
            if not no_done:
                self.branch(end)
            if yes_done and no_done:
                self.terminated = True
            else:
                self.mark(end)
        elif s.tag == "while":
            e, body = p
            cond, loop, end = self.fresh("check"), self.fresh("strut"), self.fresh("end")
            self.branch(cond)
            self.mark(cond)
            typ, val = self.expression(e)
            self.require(typ, "yass", e.token)
            self.emit(f"br i1 {val}, label %{loop}, label %{end}")
            self.mark(loop)
            self.block(body)
            if not self.terminated:
                self.branch(cond)
            self.mark(end)

    def compile(self) -> str:
        for i, (token, typ) in enumerate(self.params):
            ptr = self.bind(str(token.value), typ, token)
            self.emit(f"store {TYPES[typ]} %arg{i}, ptr {ptr}")
        # Parameters and the outer function body share a scope.
        for stmt in self.statements:
            if self.terminated:
                raise CompileError(stmt.token, "unreachable statement; she's already left the party")
            self.statement(stmt)
        if not self.terminated:
            if self.ret != "ghost":
                raise CompileError(self.node.token, f"bestie {self.name} can leave without gimme {self.ret}")
            self.emit("ret void")
        params = ", ".join(f"{TYPES[typ]} %arg{i}" for i, (_, typ) in enumerate(self.params))
        return f"define {TYPES[self.ret]} @bimbo_fn_{self.name}({params}) {{\nentry:\n" + "\n".join(self.allocas + self.code) + "\n}"


def compile_source(path: Path) -> str:
    source = path.read_text(encoding="utf-8")
    try:
        return Compiler(Parser(source).program(), str(path)).compile()
    except CompileError as e:
        lines = source.splitlines()
        snippet = lines[e.token.line - 1] if e.token.line <= len(lines) else ""
        raise SystemExit(f"{path}:{e.token.line}:{e.token.column}: bimbo error: {e.message}\n  {snippet}\n  {' ' * (e.token.column - 1)}^") from None


def build(ir: str, output: Path, clang: str, opt: str, sanitize: bool):
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bimbo-build-") as tmp:
        ll = Path(tmp) / "out.ll"
        if sanitize:
            # LLVM's ASan pass instruments functions carrying this attribute.
            ir = ir.replace(") {\n", ") sanitize_address {\n")
        ll.write_text(ir, encoding="utf-8")
        command = [clang, f"-O{opt}", "-Wno-override-module", "-std=c11", "-Wall", "-Wextra", "-Werror",
                   str(ll), str(ROOT / "runtime" / "glitter.c"), "-o", str(output)]
        if sanitize:
            command += ["-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-g"]
        subprocess.run(command, check=True)


def main():
    parser = argparse.ArgumentParser(description="bimbo-lang: no thoughts, just LLVM 💅")
    parser.add_argument("command", choices=["build", "emit", "check", "run"])
    parser.add_argument("source", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("-O", choices=["0", "1", "2", "3"], default="2")
    parser.add_argument("--clang", default=os.environ.get("CLANG", "clang"))
    parser.add_argument("--sanitize", action="store_true")
    args = parser.parse_args()
    try:
        ir = compile_source(args.source)
        if args.command == "emit":
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(ir, encoding="utf-8")
            else:
                sys.stdout.write(ir)
        elif args.command == "build":
            build(ir, args.output or args.source.with_suffix(""), args.clang, args.O, args.sanitize)
        elif args.command == "run":
            with tempfile.TemporaryDirectory(prefix="bimbo-run-") as tmp:
                executable = Path(tmp) / "bestie"
                build(ir, executable, args.clang, args.O, args.sanitize)
                return subprocess.run([str(executable)]).returncode
    except (OSError, subprocess.CalledProcessError) as e:
        parser.exit(1, f"bimbo error: {e}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
