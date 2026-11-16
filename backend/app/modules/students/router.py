"""
RIT Sync Vision - Student Management API Router
"""

from typing import List
from fastapi import APIRouter, Depends, status

from backend.app.database.session import get_db
from backend.app.modules.authentication.dependencies import get_current_user, require_admin
from backend.app.modules.students.models import Student
from backend.app.modules.students.schemas import StudentCreate, StudentResponse, StudentUpdate
from backend.app.modules.students.service import student_service
from backend.app.modules.users.models import User

router = APIRouter(prefix="/students", tags=["Students"])


@router.get(
    "/",
    response_model=List[StudentResponse],
    summary="List Students",
    description="Retrieve all registered students (Teacher or Admin).",
)
def list_students(
    skip: int = 0,
    limit: int = 100,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List students with pagination. Accessible to Teachers and Admins."""
    return student_service.list_students(db, skip=skip, limit=limit)


@router.post(
    "/",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Student",
    description="Register a new student record (Admin only).",
)
def create_student(
    student_in: StudentCreate,
    db=Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Create a new student record. Restricted to administrators."""
    return student_service.create_student(db, student_in=student_in)


@router.get(
    "/{student_id}",
    response_model=StudentResponse,
    summary="Get Student Details",
    description="Retrieve student details by institutional student identifier string (Teacher or Admin).",
)
def get_student(
    student_id: str,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve details for a single student by institutional student_id."""
    return student_service.get_by_student_id(db, student_id=student_id)


@router.put(
    "/{student_id}",
    response_model=StudentResponse,
    summary="Update Student",
    description="Update an existing student record by institutional student identifier string (Admin only).",
)
def update_student(
    student_id: str,
    student_in: StudentUpdate,
    db=Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Update student record details by institutional student_id. Restricted to administrators."""
    return student_service.update_student_by_student_id(db, student_id=student_id, student_in=student_in)


@router.delete(
    "/{student_id}",
    summary="Delete Student",
    description="Delete a student record by institutional student identifier string (Admin only).",
)
def delete_student(
    student_id: str,
    db=Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Delete a student record from the database by institutional student_id. Restricted to administrators."""
    student_service.delete_student_by_student_id(db, student_id=student_id)
    return {"status": "ok", "message": f"Student with identifier '{student_id}' successfully deleted"}
