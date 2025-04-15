from collections import defaultdict
from unittest import mock

import pytest


@pytest.fixture
def test_env() -> dict[str, str]:
    return defaultdict(lambda: "dummy-test-value")


@pytest.fixture(autouse=True)
def overload_env(test_env: dict[str, str]):
    """
    Overloads the environment variables for the test session.
    """
    with mock.patch("os.environ", test_env):
        yield
