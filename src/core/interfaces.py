from abc import ABC, abstractmethod
import uuid


class ItemRepositoryABC(ABC):
    """
    Abstract contract for item storage.
    pipeline.py depends on this interface, not on repository.py directly.
    This enforces the Onion Architecture dependency rule.
    """

    @abstractmethod
    async def create(self, item_id: uuid.UUID, item) -> uuid.UUID:
        ...

    @abstractmethod
    async def update_ai_fields(
        self,
        item_id: uuid.UUID,
        vlm_desc: dict,
        embedding: bytes,
        confidence: float,
    ) -> None:
        ...

    @abstractmethod
    async def get_by_status(self, status: str) -> list:
        ...

    @abstractmethod
    async def get_by_id(self, item_id: uuid.UUID):
        ...