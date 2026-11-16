"""
RIT Sync Vision - Subject Business Logic Service
"""

from typing import Any, List, Optional
from fastapi import HTTPException, status

from backend.app.modules.subjects.models import Subject
from backend.app.modules.subjects.repository import subject_repository
from backend.app.modules.subjects.schemas import SubjectCreate, SubjectUpdate


class SubjectService:
    """Service handling subject/course management business rules and constraints."""

    def __init__(self, repo=subject_repository):
        self.repo = repo

    def get_by_id(self, db: Any, id: int) -> Subject:
        subject = self.repo.get_by_id(db, id=id)
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subject with id {id} not found",
            )
        return subject

    def get_by_subject_code(self, db: Any, subject_code: str) -> Subject:
        subject = self.repo.get_by_subject_code(db, subject_code=subject_code.strip())
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subject with code '{subject_code.strip()}' not found",
            )
        return subject

    def list_subjects(self, db: Any, skip: int = 0, limit: int = 100) -> List[Subject]:
        return self.repo.list_subjects(db, skip=skip, limit=limit)

    def create_subject(self, db: Any, subject_in: SubjectCreate) -> Subject:
        """
        Create a new subject record with unique subject_code validation.
        Admin-only operation.
        """
        existing = self.repo.get_by_subject_code(db, subject_code=subject_in.subject_code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subject code is already registered",
            )

        subject_data = {
            "subject_code": subject_in.subject_code,
            "name": subject_in.name,
            "department": subject_in.department,
            "description": subject_in.description,
            "is_active": subject_in.is_active,
        }
        return self.repo.create(db, subject_data=subject_data)

    def update_subject(self, db: Any, id: int, subject_in: SubjectUpdate) -> Subject:
        """
        Update an existing subject record.
        Admin-only operation.
        """
        subject = self.get_by_id(db, id=id)
        update_data = {}

        if subject_in.subject_code is not None:
            normalized_code = subject_in.subject_code.strip().upper()
            if normalized_code != subject.subject_code.upper():
                existing = self.repo.get_by_subject_code(db, subject_code=normalized_code)
                if existing and existing.id != subject.id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Subject code is already in use",
                    )
            update_data["subject_code"] = normalized_code

        if subject_in.name is not None:
            update_data["name"] = subject_in.name.strip()

        if subject_in.department is not None:
            update_data["department"] = subject_in.department.strip() if subject_in.department else None

        if subject_in.description is not None:
            update_data["description"] = subject_in.description.strip() if subject_in.description else None

        if subject_in.is_active is not None:
            update_data["is_active"] = subject_in.is_active

        return self.repo.update(db, subject=subject, update_data=update_data)

    def delete_subject(self, db: Any, id: int) -> bool:
        """
        Delete a subject record.
        Admin-only operation.
        """
        subject = self.get_by_id(db, id=id)
        return self.repo.delete(db, subject=subject)


subject_service = SubjectService()
