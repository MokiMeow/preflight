"""Adversarial in-memory artifact paths, private files, links and duplicates."""

import importlib.util
import io
import stat
import tarfile
import warnings
import zipfile
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "distribution_probe", Path("scripts/verify_distribution.py")
)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


@pytest.mark.parametrize(
    "name",
    [
        "../escaped.txt",
        "/escaped.txt",
        "other/file.txt",
        "package/../escaped.txt",
        "package/.worktrees/child/.env.example",
    ],
)
def test_source_rejects_original_path_before_prefix_removal(name):
    with pytest.raises(SystemExit):
        probe.member_path(name, {"package"}, allow_env_example=True)


@pytest.mark.parametrize(
    "name", [".env", "../escaped.txt", "preflight/.env", "preflight/../escaped.txt"]
)
def test_wheel_inspects_every_member(name):
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as wheel:
        for i in range(17):
            wheel.writestr(f"preflight/module{i}.py", "")
        wheel.writestr(name, "synthetic marker")
    data.seek(0)
    with zipfile.ZipFile(data) as wheel, pytest.raises(SystemExit):
        probe.inspect_wheel_members(wheel, "package.dist-info")


@pytest.mark.parametrize("kind", ["duplicate", "link"])
def test_wheel_duplicate_or_link_refused(kind):
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as wheel:
        wheel.writestr("preflight/a.py", "")
        if kind == "duplicate":
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                wheel.writestr("preflight/a.py", "")
        else:
            info = zipfile.ZipInfo("preflight/link")
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            wheel.writestr(info, "a.py")
    data.seek(0)
    with zipfile.ZipFile(data) as wheel, pytest.raises(SystemExit):
        probe.inspect_wheel_members(wheel, "package.dist-info")


def test_source_duplicate_refused_and_root_example_supported():
    assert probe.member_path("package/.env.example", {"package"}, True) == "package/.env.example"
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w") as archive:
        archive.addfile(tarfile.TarInfo("package/a.py"))
        archive.addfile(tarfile.TarInfo("package/a.py"))
    data.seek(0)
    with tarfile.open(fileobj=data) as archive, pytest.raises(SystemExit):
        probe.inspect_source_members(archive, "package")
