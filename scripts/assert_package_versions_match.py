import tomli

import p3orm


def assert_versions_equal():
    with open("pyproject.toml", "rb") as pyproject:
        toml = tomli.load(pyproject)

    assert p3orm.__version__ == toml["tool"]["poetry"]["version"], "pyproject.toml and p3orm.__version__ mismatch"


if __name__ == "__main__":
    assert_versions_equal()
