# backend/models.py

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    serial_code = Column(String, unique=True, index=True)
    store = Column(String, index=True)
    item_url = Column(String, unique=True)
    image_url = Column(String)
    
    # This creates the one-to-many relationship. One Item can have many PriceHistory records.
    prices = relationship("PriceHistory", back_populates="item")

class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    item_id = Column(Integer, ForeignKey("items.id"))

    # This links back to the Item class.
    item = relationship("Item", back_populates="prices")