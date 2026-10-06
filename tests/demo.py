"""Run the makeover in a disposable directory, never in the source checkout."""
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="bimbo-closet-") as tmp:
    subprocess.run([root / "build/json2dir"], input=(root / "examples/closet.json").read_bytes(), cwd=tmp, check=True)
    print("💅📁✨ Filesystem makeover: your directory tree just booked a nail appointment")
    for path in sorted(Path(tmp).rglob("*")):
        label = str(path.relative_to(tmp))
        if path.is_symlink():
            print("  " + label + " -> " + str(path.readlink()))
        elif path.is_dir():
            print("  " + label + "/")
        else:
            print("  " + label)
    sys.stdout.flush()
    subprocess.run([Path(tmp) / "slay.sh"], check=True)
