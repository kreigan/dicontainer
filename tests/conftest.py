from pathlib import Path


FIXTURES_PATH = "tests/fixtures"

# Import all fixtures from the fixtures directory
pytest_plugins = [
    str(fixture).replace("/", ".").removesuffix(".py")
    for fixture in Path(FIXTURES_PATH).rglob("[!__]*.py")
]
