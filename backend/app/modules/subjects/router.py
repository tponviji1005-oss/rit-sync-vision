"""
RIT Sync Vision - Subject Management API Router
"""

from typing import List
from fastapi import APIRouter, Depends, status

from backend.app.database.session import get_db
from backend.app.modules.authentication.dependencies import get_current_user, require_admin
from backend.app.modules.subjects.schemas import (
    SubjectCreate,
    SubjectResponse,
    SubjectUpdate,
)
from backend.app.modules.subjects.service import subject_service
from backend.app.modules.users.models import User

router = APIRouter(prefix="/subjects", tags=["Subjects"])


@router.get(
    "/",
    response_model=List[SubjectResponse],
    summary="List Subjects",
    description="Retrieve all registered subjects (Teacher or Admin).",
)
def list_subjects(
    skip: int = 0,
    limit: int = 100,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List subjects with pagination. Accessible to Teachers and Admins."""
    return subject_service.list_subjects(db, skip=skip, limit=limit)


@router.post(
    "/",
    response_model=SubjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Subject",
    description="Register a new subject record (Admin only).",
)
def create_subject(
    subject_in: SubjectCreate,
    db=Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Create a new subject. Restricted to administrators."""
    return subject_service.create_subject(db, subject_in=subject_in)


@router.get(
    "/{subject_id}",
    response_model=SubjectResponse,
    summary="Get Subject Details",
    description="Retrieve subject details by database ID (Teacher or Admin).",
)
def get_subject(
    subject_id: int,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve details for a single subject by ID."""
    return subject_service.get_by_id(db, id=subject_id)


@router.put(
    "/{subject_id}",
    response_model=SubjectResponse,
    summary="Update Subject",
    description="Update an existing subject record by ID (Admin only).",
)
def update_subject(
    subject_id: int,
    subject_in: SubjectUpdate,
    db=Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Update subject record details. Restricted to administrators."""
    return subject_service.update_subject(db, id=subject_id, subject_in=subject_in)


@router.delete(
    "/{subject_id}",
    summary="Delete Subject",
    description="Delete a subject record by ID (Admin only).",
)
def delete_subject(
    subject_id: int,
    db=Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Delete a subject from the database. Restricted to administrators."""
    subject_service.delete_subject(db, id=subject_id)
    return {"status": "ok", "message": f"Subject with id {subject_id} successfully deleted"}
