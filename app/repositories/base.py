from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from sqlalchemy.orm import Session
from app.database.session import Base

ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]) -> None:
        """Base repository with generic CRUD helper methods."""
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """Fetch a single record by primary key id."""
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Fetch multiple records with offset and limit parameters."""
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: Dict[str, Any]) -> ModelType:
        """Create a new record in the database."""
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: ModelType, obj_in: Dict[str, Any]) -> ModelType:
        """Update fields of an existing database record."""
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: Any) -> Optional[ModelType]:
        """Delete a record from the database by its ID."""
        obj = db.query(self.model).filter(self.model.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj
