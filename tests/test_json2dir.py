import json
import os
from pathlib import Path
import random
import stat
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("BIMBO_BINARY", ROOT / "build/json2dir")).resolve()
REFERENCE = os.environ.get("JSON2DIR_REFERENCE")


def run(binary, directory, data, *args, mask=None):
    if isinstance(data, str):
        data = data.encode()
    # A fresh process protects the test runner from the program's chdir calls.
    return subprocess.run([str(binary), *args], cwd=directory, input=data,
                          capture_output=True, timeout=10, umask=-1 if mask is None else mask)


def snapshot(directory):
    entries = []

    def walk(path, prefix):
        for entry in sorted(os.scandir(path), key=lambda e: e.name):
            name = prefix + entry.name
            mode = stat.S_IMODE(entry.stat(follow_symlinks=False).st_mode)
            if entry.is_symlink():
                entries.append((name, "link", os.readlink(entry.path)))
            elif entry.is_dir(follow_symlinks=False):
                entries.append((name, "dir", mode))
                walk(entry.path, name + "/")
            else:
                entries.append((name, "file", mode, Path(entry.path).read_bytes()))
    walk(directory, "")
    return entries


INVALID = [
    "", "f", "3 4", "{} {}", "[]", '"hi"', "null", "true", "false", "3", "-1.2e3",
    '{"foo/bar":""}', '{"":""}', '{"/":""}', '{".":""}', '{"..":""}',
    '{"./foo":""}', '{"foo/../bar":""}', '{"/absolute":""}',
    '{"x":1}', '{"x":null}', '{"x":true}', '{"x":false}',
    '{"x":[]}', '{"x":["link"]}', '{"x":["link","y","z"]}', '{"x":[1,2]}',
    '{"x":["link",{}]}', '{"x":["linksym","y"]}',
    '{"x":}', '{"x":"y",}', '{x:"y"}', '{"x":"y"', '{"x" "y"}',
    '{"x":["link","y",]}', '{"x":"\\q"}', '{"x":"\n"}',
    '{"x":"\\uD800"}', '{"x":"\\uDC00"}', '{"x":"\\uD800\\u0041"}',
    '{"x":"\\uZZZZ"}', '{"x":01}', '{"x":+1}', '{"x":1.}', '{"x":1e}',
    '{"x":1e+}', '{"x":.1}', '{"x":NaN}', '{"x":Infinity}', '{"x":1e309}',
    '{"x":"unterminated}', '\ufeff{}', '{"x":"\t"}', '{"a":"x"} garbage',
    '{"a\\u0000b":"x"}', '{"x":["link","a\\u0000b"]}',
    b'\xff', b'{"x":"\xc0\x80"}', b'{"x":"\xed\xa0\x80"}',
    b'{"x":"\xf4\x90\x80\x80"}', b'{"x":"\xe2\x82"}',
]


def random_tree(rng, depth=0):
    result = {}
    for i in range(rng.randrange(0, 7)):
        name = f"{i}_" + rng.choice(["bestie", "pink", "💅", "привет", "a b", "back\\slash"])
        choice = rng.randrange(4 if depth < 4 else 3)
        if choice == 0:
            result[name] = rng.choice(["", "💅\nпривет", "a\x00b", "quote\"\\\t\b\f\r", "slay"])
        elif choice == 1:
            result[name] = ["script", "#!/bin/sh\nprintf '%s\\n' slay\n"]
        elif choice == 2:
            result[name] = ["link", "../some target 💅"]
        else:
            result[name] = random_tree(rng, depth + 1)
    return result


class Json2DirTests(unittest.TestCase):
    def test_example(self):
        with tempfile.TemporaryDirectory(prefix="bimbo-example-") as tmp:
            p = run(BINARY, tmp, (ROOT / "examples/closet.json").read_bytes())
            self.assertEqual(p.returncode, 0, p.stderr.decode())
            self.assertEqual(p.stdout, b"")
            self.assertEqual((Path(tmp) / "diary.txt").read_text(), "Dear diary, today I compiled my situationship to LLVM.\n")
            self.assertEqual(os.readlink(Path(tmp) / "ex"), "walk-in-closet/outfit.txt")
            mode = (Path(tmp) / "slay.sh").stat().st_mode
            self.assertEqual(mode & 0o111, 0o111)
            script = subprocess.run([Path(tmp) / "slay.sh"], capture_output=True, check=True)
            self.assertEqual(script.stdout.decode(), "no thoughts, just directory trees 💅\n")

    def test_invalid_inputs(self):
        for data in INVALID:
            with self.subTest(data=data), tempfile.TemporaryDirectory(prefix="bimbo-invalid-") as tmp:
                p = run(BINARY, tmp, data)
                self.assertEqual(p.returncode, 1, p.stderr)
                self.assertTrue(p.stderr.startswith(b"Error:"), p.stderr)
                self.assertEqual(snapshot(tmp), [])

    def test_arguments(self):
        with tempfile.TemporaryDirectory(prefix="bimbo-usage-") as tmp:
            for arg in ("--help", "--version", "file.json"):
                p = run(BINARY, tmp, "{}", arg)
                self.assertEqual(p.returncode, 1)
                self.assertIn(b"Usage:", p.stderr)

    def test_unicode_escapes_and_binary_string_content(self):
        data = r'{"\u043f\u0440\u0438\u0432\u0435\u0442":"\uD83D\uDC85\u0000\/\"\\\b\f\n\r\t"}'
        with tempfile.TemporaryDirectory(prefix="bimbo-unicode-") as tmp:
            p = run(BINARY, tmp, data)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual((Path(tmp) / "привет").read_bytes(), "💅\x00/\"\\\b\f\n\r\t".encode())

    def test_overwrite_merge_and_symlink_replacement(self):
        with tempfile.TemporaryDirectory(prefix="bimbo-overwrite-") as tmp:
            root = Path(tmp)
            (root / "dir").mkdir()
            (root / "dir/keep").write_text("keep")
            (root / "regular").write_text("old")
            (root / "target").write_text("untouched")
            (root / "link").symlink_to("target")
            (root / "become_dir").write_text("old")
            data = json.dumps({"dir": {"new": "new"}, "regular": "new", "link": "replacement", "become_dir": {}})
            p = run(BINARY, tmp, data)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual((root / "dir/keep").read_text(), "keep")
            self.assertEqual((root / "dir/new").read_text(), "new")
            self.assertEqual((root / "regular").read_text(), "new")
            self.assertFalse((root / "link").is_symlink())
            self.assertEqual((root / "target").read_text(), "untouched")
            self.assertTrue((root / "become_dir").is_dir())

    def test_existing_directory_is_not_recursively_removed(self):
        for value in ("new", ["script", "new"], ["link", "target"]):
            with self.subTest(value=value), tempfile.TemporaryDirectory(prefix="bimbo-dir-") as tmp:
                (Path(tmp) / "foo").mkdir()
                (Path(tmp) / "foo/keep").write_text("keep")
                p = run(BINARY, tmp, json.dumps({"foo": value}))
                self.assertEqual(p.returncode, 1)
                self.assertEqual((Path(tmp) / "foo/keep").read_text(), "keep")

    def test_duplicate_keys_last_wins(self):
        with tempfile.TemporaryDirectory(prefix="bimbo-duplicates-") as tmp:
            p = run(BINARY, tmp, '{"x":null,"x":"last","z":"old","z":{"y":"new"}}')
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual((Path(tmp) / "x").read_text(), "last")
            self.assertEqual((Path(tmp) / "z/y").read_text(), "new")

    def test_sorted_keys_and_partial_semantic_failure(self):
        with tempfile.TemporaryDirectory(prefix="bimbo-order-") as tmp:
            (Path(tmp) / "b").write_text("old")
            p = run(BINARY, tmp, '{"z":"later","b":false,"a":"first"}')
            self.assertEqual(p.returncode, 1)
            self.assertEqual((Path(tmp) / "a").read_text(), "first")
            self.assertFalse((Path(tmp) / "b").exists())
            self.assertFalse((Path(tmp) / "z").exists())

    def test_entire_json_parsed_before_writes(self):
        with tempfile.TemporaryDirectory(prefix="bimbo-parse-first-") as tmp:
            (Path(tmp) / "a").write_text("old")
            p = run(BINARY, tmp, '{"a":"new","b":')
            self.assertEqual(p.returncode, 1)
            self.assertEqual((Path(tmp) / "a").read_text(), "old")

    def test_cannot_escape_root(self):
        with tempfile.TemporaryDirectory(prefix="bimbo-no-escape-") as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            sentinel = Path(tmp) / "sentinel"
            sentinel.write_text("safe")
            for name in ("../sentinel", str(sentinel), "dir/../../sentinel"):
                p = run(BINARY, root, json.dumps({name: "oops"}))
                self.assertEqual(p.returncode, 1)
                self.assertEqual(sentinel.read_text(), "safe")

    def test_script_mode_respects_umask_then_adds_execute(self):
        with tempfile.TemporaryDirectory(prefix="bimbo-mode-") as tmp:
            p = run(BINARY, tmp, '{"script":["script",""],"file":""}', mask=0o077)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(stat.S_IMODE((Path(tmp) / "file").stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE((Path(tmp) / "script").stat().st_mode), 0o711)

    @unittest.skipIf(os.geteuid() == 0, "root bypasses Unix permissions")
    def test_unsearchable_directory(self):
        with tempfile.TemporaryDirectory(prefix="bimbo-permission-") as tmp:
            path = Path(tmp) / "foo"
            path.mkdir()
            path.chmod(0o600)
            try:
                p = run(BINARY, tmp, '{"foo":{}}')
                self.assertEqual(p.returncode, 1)
            finally:
                path.chmod(0o700)

    def test_depth_limit(self):
        for depth in (1, 126, 127, 128, 2000):
            with self.subTest(depth=depth), tempfile.TemporaryDirectory(prefix="bimbo-depth-") as tmp:
                # Arrays need not touch the filesystem; their grammar still exercises the depth limit.
                data = '{"x":' + '[' * (depth - 1) + '"s"' + ']' * (depth - 1) + '}'
                p = run(BINARY, tmp, data)
                self.assertEqual(p.returncode, 0 if depth == 1 else 1)
                self.assertNotIn(b"AddressSanitizer", p.stderr)
                if depth >= 128:
                    self.assertIn(b"convert stdin to JSON", p.stderr)

    def test_generated_valid_trees(self):
        rng = random.Random(0xB1B0)
        for i in range(100):
            with self.subTest(case=i), tempfile.TemporaryDirectory(prefix="bimbo-generated-") as tmp:
                tree = random_tree(rng)
                p = run(BINARY, tmp, json.dumps(tree, ensure_ascii=i % 2 == 0))
                self.assertEqual(p.returncode, 0, p.stderr)


@unittest.skipUnless(REFERENCE, "set JSON2DIR_REFERENCE to a compiled Rust json2dir for differential tests")
class DifferentialTests(unittest.TestCase):
    def compare(self, data, setup=None, mask=None):
        with tempfile.TemporaryDirectory(prefix="bimbo-oracle-") as tmp:
            left, right = Path(tmp) / "bimbo", Path(tmp) / "rust"
            left.mkdir()
            right.mkdir()
            if setup:
                setup(left)
                setup(right)
            a, b = run(BINARY, left, data, mask=mask), run(REFERENCE, right, data, mask=mask)
            self.assertEqual(a.returncode, b.returncode, (data, a.stderr, b.stderr))
            self.assertEqual(a.stdout, b.stdout)
            self.assertEqual(snapshot(left), snapshot(right), (data, a.stderr, b.stderr))

    def test_original_contract_and_invalid_input(self):
        for data in INVALID + ["{}", ' { "x" : "hello" } \r\n', '{"x":"a\\u0000b"}', '{"x":"\\uD83D\\uDC85"}',
                               '{"x":null,"x":"last"}', '{"z":"new","a":"first"}',
                               '{"x":1e-9999}', '{"x":-0}', '{"x":1.7976931348623157e308}',
                               '{"x":["link",""]}', '{"foo/./":{}}', '{"foo//":{}}',
                               '{"foo/.":"x"}', '{"foo/":"x"}', '{"foo\\bar":"x"}',
                               '{"///":"x"}', '{"./":"x"}', '{"foo/../":"x"}']:
            with self.subTest(data=data):
                self.compare(data)

    def test_generated_trees(self):
        rng = random.Random(0xC0FFEE)
        for i in range(200):
            with self.subTest(case=i):
                self.compare(json.dumps(random_tree(rng), ensure_ascii=i % 2 == 0), mask=0o077 if i % 3 == 0 else 0o022)

    def test_replacement_and_partial_failures(self):
        def setup(path):
            (path / "foo").mkdir()
            (path / "foo/keep").write_text("keep")
            (path / "target").write_text("untouched")
            (path / "link").symlink_to("target")
            (path / "file").write_text("old")
        cases = [
            '{"foo":{},"link":"new","file":{}}', '{"foo":"new"}',
            '{"foo":["link","target"]}', '{"foo":["script","new"]}',
            '{"file":false}', '{"link":false}', '{"z":"later","file":null,"a":"first"}',
            '{"file":["script","x"],"link":["link","file"]}', '{"foo":{"new":"x"}}',
            '{"foo/.":{}}', '{"foo/.":"x"}', '{"file/.":"x"}', '{"file/":"x"}',
        ]
        for data in cases:
            with self.subTest(data=data):
                self.compare(data, setup)

    def test_depth_boundaries(self):
        for depth in (126, 127, 128):
            with self.subTest(depth=depth):
                self.compare('{"x":' + '[' * (depth - 1) + '"s"' + ']' * (depth - 1) + '}')

    def test_number_range_and_rounding_before_writes(self):
        numbers = [
            '0e9999', '-0e9999', '1e309', '1e-9999', '1.7976931348623157e308',
            '1.7976931348623158e308', '1.7976931348623159e308',
            '9' * 1000 + 'e-1000', '0.' + '0' * 1000 + '1e1001',
            '18446744073709551615', '18446744073709551616', '1e2147483648', '1e-2147483648',
        ]
        rng = random.Random(808)
        for i in range(100):
            mantissa = str(rng.randrange(1, 10)) + '.' + ''.join(str(rng.randrange(10)) for _ in range(rng.randrange(1, 40)))
            numbers.append(mantissa + 'e' + str(rng.choice([-1000, -309, -308, 0, 307, 308, 309, 1000])))
        for number in numbers:
            with self.subTest(number=number[:100]):
                self.compare('{"a":"before","x":' + number + '}')

    def test_mutated_json(self):
        rng = random.Random(31337)
        original = b'{"a":"hello\\n\\uD83D\\uDC85","b":{"c":"world"},"d":["link","a"]}'
        for i in range(100):
            mutated = bytearray(original)
            index = rng.randrange(len(mutated))
            mutated[index] = rng.randrange(256)
            with self.subTest(case=i):
                self.compare(bytes(mutated))


if __name__ == "__main__":
    unittest.main()
