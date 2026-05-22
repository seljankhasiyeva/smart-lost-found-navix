import pytest
from src.core.exceptions import ItemNotFound, StorageError, ProviderError


def test_item_not_found_is_exception():
    with pytest.raises(ItemNotFound):
        raise ItemNotFound("test id")


def test_storage_error_message():
    err = StorageError("db down")
    assert "db down" in str(err)


def test_provider_error_is_exception():
    err = ProviderError("timeout")
    assert isinstance(err, Exception)


def test_item_not_found_inherits_exception():
    assert issubclass(ItemNotFound, Exception)


def test_storage_error_inherits_exception():
    assert issubclass(StorageError, Exception)


def test_provider_error_inherits_exception():
    assert issubclass(ProviderError, Exception)