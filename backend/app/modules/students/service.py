"""
RIT Sync Vision - Student Business Logic Service
"""

from typing import Any, List, Optional
from fastapi import HTTPException, status

from backend.app.modules.students.models import Student
from backend.app.modules.students.repository import student_repository
from backend.app.modules.students.schemas import StudentCreate, StudentUpdate


class StudentService:
    """Service handling student registration and management business rules."""

    def __init__(self, repo=student_repository):
        self.repo = repo

    def get_by_id(self, db: Any, id: int) -> Student:
        student = self.repo.get_by_id(db, id=id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student with id {id} not found",
            )
        return student

    def get_by_student_id(self, db: Any, student_id: str) -> Student:
        student = self.repo.get_by_student_id(db, student_id=student_id.strip())
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student with student_id '{student_id.strip()}' not found",
            )
        return student

    def list_students(self, db: Any, skip: int = 0, limit: int = 100) -> List[Student]:
        return self.repo.list_students(db, skip=skip, limit=limit)

    def create_student(self, db: Any, student_in: StudentCreate) -> Student:
        """
        Register a new student record with uniqueness verification.
        Admin-only operation.
        """
        # Validate unique student_id
        existing_student = self.repo.get_by_student_id(db, student_id=student_in.student_id)
        if existing_student:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student identifier is already registered",
            )

        # Validate unique email if provided
        if student_in.email:
            existing_email = self.repo.get_by_email(db, email=student_in.email)
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Student email is already registered",
                )

        student_data = {
            "student_id": student_in.student_id,
            "first_name": student_in.first_name,
            "last_name": student_in.last_name,
            "email": student_in.email,
            "is_active": student_in.is_active,
            "is_enrolled": student_in.is_enrolled,
        }
        return self.repo.create(db, student_data=student_data)

    def update_student(self, db: Any, id: int, student_in: StudentUpdate) -> Student:
        student = self.get_by_id(db, id=id)
        return self._apply_update(db, student=student, student_in=student_in)

    def update_student_by_student_id(self, db: Any, student_id: str, student_in: StudentUpdate) -> Student:
        student = self.get_by_student_id(db, student_id=student_id)
        return self._apply_update(db, student=student, student_in=student_in)

    def _apply_update(self, db: Any, student: Student, student_in: StudentUpdate) -> Student:
        update_data = {}

        if student_in.first_name is not None:
            update_data["first_name"] = student_in.first_name.strip()

        if student_in.last_name is not None:
            update_data["last_name"] = student_in.last_name.strip()

        if student_in.email is not None:
            normalized_email = student_in.email.strip().lower()
            current_email = student.email.lower() if student.email else None
            if normalized_email != current_email:
                existing = self.repo.get_by_email(db, email=normalized_email)
                if existing and existing.id != student.id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Student email is already in use",
                    )
            update_data["email"] = normalized_email

        if student_in.is_active is not None:
            update_data["is_active"] = student_in.is_active

        if student_in.is_enrolled is not None:
            update_data["is_enrolled"] = student_in.is_enrolled

        return self.repo.update(db, student=student, update_data=update_data)

    def delete_student(self, db: Any, id: int) -> bool:
        student = self.get_by_id(db, id=id)
        return self.repo.delete(db, student=student)

    def delete_student_by_student_id(self, db: Any, student_id: str) -> bool:
        student = self.get_by_student_id(db, student_id=student_id)
        return self.repo.delete(db, student=student)


student_service = StudentService()
