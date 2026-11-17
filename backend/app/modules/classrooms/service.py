"""
RIT Sync Vision - Classroom Business Logic Service
"""

from typing import Any, List, Optional
from fastapi import HTTPException, status

from backend.app.modules.classrooms.models import Classroom
from backend.app.modules.classrooms.repository import classroom_repository
from backend.app.modules.classrooms.schemas import ClassroomCreate, ClassroomUpdate


class ClassroomService:
    """Service handling classroom management business rules and constraints."""

    def __init__(self, repo=classroom_repository):
        self.repo = repo

    def get_by_id(self, db: Any, id: int) -> Classroom:
        classroom = self.repo.get_by_id(db, id=id)
        if not classroom:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Classroom with id {id} not found",
            )
        return classroom

    def get_by_room_number(self, db: Any, room_number: str) -> Classroom:
        classroom = self.repo.get_by_room_number(db, room_number=room_number.strip())
        if not classroom:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Classroom with room number '{room_number.strip()}' not found",
            )
        return classroom

    def list_classrooms(self, db: Any, skip: int = 0, limit: int = 100) -> List[Classroom]:
        return self.repo.list_classrooms(db, skip=skip, limit=limit)

    def create_classroom(self, db: Any, classroom_in: ClassroomCreate) -> Classroom:
        """
        Create a new classroom record with uniqueness validation.
        Admin-only operation.
        """
        existing = self.repo.get_by_room_number(db, room_number=classroom_in.room_number)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Classroom room number is already registered",
            )

        classroom_data = {
            "room_number": classroom_in.room_number,
            "name": classroom_in.name,
            "capacity": classroom_in.capacity,
            "camera_stream_url": classroom_in.camera_stream_url,
            "is_active": classroom_in.is_active,
        }
        return self.repo.create(db, classroom_data=classroom_data)

    def update_classroom(self, db: Any, id: int, classroom_in: ClassroomUpdate) -> Classroom:
        """
        Update an existing classroom record.
        Admin-only operation.
        """
        classroom = self.get_by_id(db, id=id)
        update_data = {}

        if classroom_in.room_number is not None:
            normalized_room = classroom_in.room_number.strip().upper()
            if normalized_room != classroom.room_number.upper():
                existing = self.repo.get_by_room_number(db, room_number=normalized_room)
                if existing and existing.id != classroom.id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Classroom room number is already in use",
                    )
            update_data["room_number"] = normalized_room

        if classroom_in.name is not None:
            update_data["name"] = classroom_in.name.strip()

        if classroom_in.capacity is not None:
            update_data["capacity"] = classroom_in.capacity

        if classroom_in.camera_stream_url is not None:
            update_data["camera_stream_url"] = classroom_in.camera_stream_url.strip() if classroom_in.camera_stream_url else None

        if classroom_in.is_active is not None:
            update_data["is_active"] = classroom_in.is_active

        return self.repo.update(db, classroom=classroom, update_data=update_data)

    def delete_classroom(self, db: Any, id: int) -> bool:
        """
        Delete a classroom record.
        Admin-only operation.
        """
        classroom = self.get_by_id(db, id=id)
        return self.repo.delete(db, classroom=classroom)


classroom_service = ClassroomService()
