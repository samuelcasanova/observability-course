from enum import Enum
from typing import List

from pydantic import BaseModel


class OrderStatus(str, Enum):
    RECEIVED = "received"
    PREPARING = "preparing"
    READY = "ready"
    IN_DELIVERY = "in_delivery"
    DELIVERED = "delivered"
    FAILED = "failed"


class OrderRequest(BaseModel):
    restaurant: str
    items: List[str]
    customer: str


class Order(BaseModel):
    id: str
    restaurant: str
    items: List[str]
    customer: str
    status: OrderStatus
