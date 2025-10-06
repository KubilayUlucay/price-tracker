# backend/main.py

from typing import List
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/items/{item_id}/prices/", response_model=schemas.PriceHistoryCreate)
def create_price_for_item(item_id: int, price: schemas.PriceHistoryCreate, db: Session = Depends(get_db)):
    db_price = models.PriceHistory(**price.dict(), item_id=item_id)
    db.add(db_price)
    db.commit()
    db.refresh(db_price)
    return db_price


# --- NEW ENDPOINT STARTS HERE ---
@app.get("/items/by_serial_code/{serial_code}", response_model=schemas.Item)
def read_item_by_serial_code(serial_code: str, db: Session = Depends(get_db)):
    db_item = db.query(models.Item).filter(models.Item.serial_code == serial_code).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item
# --- NEW ENDPOINT ENDS HERE ---

@app.get("/items/", response_model=List[schemas.Item])
def read_items(db: Session = Depends(get_db)):
    items = db.query(models.Item).all()
    return items

@app.post("/items/", response_model=schemas.Item)
def create_item(item: schemas.ItemCreate, db: Session = Depends(get_db)):
    # Check if item already exists
    db_item = db.query(models.Item).filter(models.Item.serial_code == item.serial_code).first()
    if db_item:
        raise HTTPException(status_code=400, detail="Serial code already registered")
    
    db_item = models.Item(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/")
def read_root():
    return {"status": "API is running"}