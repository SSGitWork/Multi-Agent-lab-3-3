"""conftest.py — Lab 3.3"""
import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-llm",
        action="store_true",
        default=False,
        help="Run tests that make live LLM or MCP calls.",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if config.getoption("--run-llm"):
        return
    skip_llm = pytest.mark.skip(reason="Live call — pass --run-llm to enable.")
    for item in items:
        if "llm" in item.keywords:
            item.add_marker(skip_llm)
