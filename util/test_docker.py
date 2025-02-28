import pytest
from util.docker import mount
from pathlib import Path


@pytest.mark.parametrize("path", ["", "/file.jpg",
                                  "/projects",
                                  "/some/file.jpg",
                                  "/long/path/into/"
                                  ])
def test_mount(path):
    output = mount(Path(path))
    assert output.startswith("-v")
    assert not "/:/" in output
