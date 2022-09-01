import pytest

from p3orm.core import driver


@pytest.fixture(autouse=True, scope="function")
async def disconnect_after_test():

    yield

    await driver().disconnect()
