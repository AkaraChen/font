"""The release archive has to be a function of its inputs and nothing else.

`package-release.sh` used `zip -9 -r`, which stamps every member with the local
mtime and walks the staging directory in readdir order. Two builds of identical
products therefore produced two different archives, so nothing downstream could
compare a release against the products it claims to hold. Since the products are
store paths now, that is the only remaining source of nondeterminism in a
release — worth a test rather than a comment.
"""

from __future__ import annotations

import zipfile

from fontkit import package


def _run(tmp_path, *, name="A.ttf", body=b"font-bytes"):
    src = tmp_path / "src"
    src.mkdir(parents=True, exist_ok=True)
    font = src / name
    font.write_bytes(body)
    readme = src / "README.txt"
    readme.write_text("hello\n")
    licence = src / "OFL.txt"
    licence.write_text("licence\n")

    out = tmp_path / "out"
    package.main(
        [
            str(font),
            "--stem",
            "Demo",
            "--version",
            "1.2.3",
            "--out",
            str(out),
            "--readme",
            str(readme),
            "--license",
            str(licence),
        ]
    )
    return out / "Demo-1.2.3.zip"


def test_archive_holds_fonts_licences_and_readme(tmp_path):
    archive = _run(tmp_path)
    with zipfile.ZipFile(archive) as zf:
        assert sorted(zf.namelist()) == ["A.ttf", "OFL.txt", "README.txt"]
        assert zf.read("A.ttf") == b"font-bytes"


def test_version_v_prefix_is_stripped(tmp_path):
    src = tmp_path / "f.ttf"
    src.write_bytes(b"x")
    out = tmp_path / "out"
    package.main([str(src), "--stem", "Demo", "--version", "v0.1.0", "--out", str(out)])
    assert (out / "Demo-0.1.0.zip").is_file()


def test_same_inputs_produce_byte_identical_archives(tmp_path):
    first = _run(tmp_path / "a").read_bytes()
    second = _run(tmp_path / "b").read_bytes()
    assert first == second


def test_member_order_does_not_depend_on_argument_order(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    for name in ("B.ttf", "A.ttf"):
        (src / name).write_bytes(name.encode())

    def build(order, out):
        package.main(
            [*(str(src / n) for n in order), "--stem", "D", "--version", "1", "--out", str(out)]
        )
        return (out / "D-1.zip").read_bytes()

    assert build(["A.ttf", "B.ttf"], tmp_path / "x") == build(["B.ttf", "A.ttf"], tmp_path / "y")
