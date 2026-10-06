from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "compiler"))
from bimboc import Compiler, CompileError, Parser, build


def compile_text(source):
    return Compiler(Parser(source).program(), "test.bimbo").compile()


class CompilerTests(unittest.TestCase):
    def test_direct_llvm_control_flow(self):
        ir = compile_text("""
bestie main() -> tea {
    glam i: tea = 0;
    strut i < 3 { i = i + 1; }
    vibecheck i == 3 && slay { gimme 0; } whatever { gimme 1; }
}
""")
        self.assertIn("define i64 @bimbo_fn_main", ir)
        self.assertIn("phi i1", ir)
        self.assertIn("br i1", ir)
        self.assertIn("add i64", ir)

    def test_diagnostics(self):
        cases = [
            ("bestie main() -> tea { gimme unknown; }", "declare her"),
            ("bestie main() -> tea { glam x: tea = slay; gimme 0; }", "wrong outfit"),
            ("bestie main() -> tea { vibecheck 1 { gimme 0; } gimme 1; }", "expected yass"),
            ("bestie main() -> tea { spill(1); gimme 0; }", "expected gloss"),
            ("bestie main() -> tea { spill(); gimme 0; }", "arguments"),
            ("bestie main() -> tea { unknown(); gimme 0; }", "unknown bestie"),
            ("bestie main() -> tea { gimme \"slay\"; }", "expected tea"),
            ("bestie main() -> tea { glam x: tea = 1; glam x: tea = 2; gimme x; }", "already has"),
            ("bestie main() -> tea { vibecheck slay { glam x: tea = 0; } gimme x; }", "declare her"),
            ("bestie main() -> tea { gimme 0; spill(\"oops\"); }", "unreachable"),
            ("bestie main() -> tea { }", "without gimme"),
            ("bestie main() -> tea { gimme 9223372036854775808; }", "overflow"),
            ("bestie main() -> tea { gimme -9223372036854775809; }", "overflow"),
            ("bestie main() -> tea { gimme " + "9" * 5000 + "; }", "overflow"),
            ("glam x: tea = 1 + 2; bestie main() -> tea { gimme 0; }", "literal"),
            ("bestie main() -> gloss { gimme \"x\"; }", "bestie main() -> tea"),
            ("bestie main(x: tea) -> tea { gimme x; }", "bestie main() -> tea"),
            ("bestie spill() -> tea { gimme 1; } bestie main() -> tea { gimme 0; }", "guest list"),
            ("bestie main() -> tea { gimme 0; } bestie main() -> tea { gimme 1; }", "guest list"),
            ("bestie main() -> tea { gimme; }", "expected ghost"),
            ("bestie main() -> tea { gimme spill(\"x\"); }", "expected tea"),
            ("bestie main() -> tea { gimme 0", "expected"),
            ('bestie main() -> tea { spill("oops); gimme 0; }', "unterminated"),
            ('bestie main() -> tea { spill("\\q"); gimme 0; }', "invalid string"),
            ("bestie main() -> tea { @; }", "guest list"),
        ]
        for source, message in cases:
            with self.subTest(message=message, source=source[:100]):
                with self.assertRaises(CompileError) as caught:
                    compile_text(source)
                self.assertIn(message, caught.exception.message)
                self.assertGreaterEqual(caught.exception.token.line, 1)

    def test_native_semantics_at_two_optimization_levels(self):
        source = r'''
💅 Short circuiting must not invite surprise side effects.
glam calls: tea = 0;
bestie side_effect() -> yass { calls = calls + 1; gimme slay; }
bestie factorial(n: tea) -> tea {
    vibecheck n <= 1 { gimme 1; } whatever { gimme n * factorial(n - 1); }
}
bestie void_return() -> ghost { gimme; }
bestie main() -> tea {
    glam a: yass = flop && side_effect();
    glam b: yass = slay || side_effect();
    glam c: yass = (slay && (flop || side_effect())) && side_effect();
    vibecheck a || !b || !c || calls != 2 { gimme 1; }
    glam sum: tea = 0;
    glam i: tea = 0;
    strut i < 5 { sum = sum + i; i = i + 1; }
    vibecheck sum != 10 || factorial(6) != 720 { gimme 2; }
    glam x: tea = 7;
    vibecheck slay { glam x: gloss = "slay"; spill(x); }
    vibecheck x != 7 { gimme 3; }
    vibecheck "-" != "-" || "slay" == "flop" || "(" != "(" { gimme 4; }
    vibecheck "a\u0000b" == "a\u0000c" { gimme 5; }
    vibecheck -7 / 3 != -2 || -7 % 3 != -1 { gimme 6; }
    vibecheck -9223372036854775808 / -1 != -9223372036854775808 { gimme 7; }
    vibecheck 9223372036854775807 + 1 != -9223372036854775808 { gimme 8; }
    void_return();
    spill("LLVM 💅 " + caption(sum));
    gimme 0;
}
'''
        ir = compile_text(source)
        with tempfile.TemporaryDirectory(prefix="bimbo-semantics-") as tmp:
            for opt in ("0", "2"):
                with self.subTest(opt=opt):
                    binary = Path(tmp) / ("native" + opt)
                    build(ir, binary, "clang", opt, False)
                    p = subprocess.run([binary], capture_output=True)
                    self.assertEqual(p.returncode, 0, p.stderr.decode())
                    self.assertEqual(p.stdout.decode(), "slay\nLLVM 💅 10\n")

    def test_runtime_arithmetic_error(self):
        with tempfile.TemporaryDirectory(prefix="bimbo-zero-") as tmp:
            binary = Path(tmp) / "native"
            build(compile_text("bestie main() -> tea { gimme 5 / 0; }"), binary, "clang", "2", False)
            p = subprocess.run([binary], capture_output=True)
            self.assertEqual(p.returncode, 1)
            self.assertIn(b"girl math has limits", p.stderr)

    def test_cli_source_location(self):
        with tempfile.TemporaryDirectory(prefix="bimbo-error-") as tmp:
            source = Path(tmp) / "bad.bimbo"
            source.write_text("bestie main() -> tea {\n    gimme unknown;\n}\n")
            p = subprocess.run([sys.executable, ROOT / "compiler/bimboc.py", "check", source], capture_output=True)
            self.assertEqual(p.returncode, 1)
            self.assertIn(b":2:11: bimbo error:", p.stderr)
            self.assertNotIn(b"Traceback", p.stderr)


if __name__ == "__main__":
    unittest.main()
