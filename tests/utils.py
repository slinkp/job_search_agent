import os
from typing import Callable

import pytest

from models import CompanyRepository


def make_clean_test_db_fixture(db_path: str) -> Callable[[], CompanyRepository]:
    """Factory for a pytest fixture that yields a clean CompanyRepository.

    Ensures the DB file at db_path is removed before and after each test,
    and yields a CompanyRepository connected to that path with clear_data=True.
    """

    @pytest.fixture(scope="function")
    def _clean_test_db():
        if os.path.exists(db_path):
            os.remove(db_path)

        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        repo = CompanyRepository(db_path=db_path, clear_data=True)
        try:
            yield repo
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    return _clean_test_db
