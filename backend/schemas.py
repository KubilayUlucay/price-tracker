# backend/schemas.py

from pydantic import BaseModel

class PriceHistoryCreate(BaseModel):
    price: float

class ItemCreate(BaseModel):
    name: str
    serial_code: str
    store: str
    item_url: str
    image_url: str

class Item(ItemCreate):
    id: int

    class Config:
        orm_mode = True