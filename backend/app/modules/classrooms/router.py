"""
RIT Sync Vision - Classroom Management API Router
"""

from typing import List
from fastapi import APIRouter, Depends, status

from backend.app.database.session import get_db
from backend.app.modules.authentication.dependencies import get_current_user, require_admin
from backend.app.modules.classrooms.schemas import (
    ClassroomCreate,
    ClassroomResponse,
    ClassroomUpdate,
)
from backend.app.modules.classrooms.service import classroom_service
from backend.app.modules.users.models import User

router = APIRouter(prefix="/classrooms", tags=["Classrooms"])


@router.get(
    "/",
    response_model=List[ClassroomResponse],
    summary="List Classrooms",
    description="Retrieve all registered classrooms (Teacher or Admin).",
)
def list_classrooms(
    skip: int = 0,
    limit: int = 100,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List classrooms with pagination. Accessible to Teachers and Admins."""
    return classroom_service.list_classrooms(db, skip=skip, limit=limit)


@router.post(
    "/",
    response_model=ClassroomResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Classroom",
    description="Register a new classroom record (Admin only).",
)
def create_classroom(
    classroom_in: ClassroomCreate,
    db=Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Create a new classroom. Restricted to administrators."""
    return classroom_service.create_classroom(db, classroom_in=classroom_in)


@router.get(
    "/{classroom_id}",
    response_model=ClassroomResponse,
    summary="Get Classroom Details",
    description="Retrieve classroom details by database ID (Teacher or Admin).",
)
def get_classroom(
    classroom_id: int,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve details for a single classroom by ID."""
    return classroom_service.get_by_id(db, id=classroom_id)


@router.put(
    "/{classroom_id}",
    response_model=ClassroomResponse,
    summary="Update Classroom",
    description="Update an existing classroom record by ID (Admin only).",
)
def update_classroom(
    classroom_id: int,
    classroom_in: ClassroomUpdate,
    db=Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Update classroom record details. Restricted to administrators."""
    return classroom_service.update_classroom(db, id=classroom_id, classroom_in=classroom_in)


@router.delete(
    "/{classroom_id}",
    summary="Delete Classroom",
    description="Delete a classroom record by ID (Admin only).",
)
def delete_classroom(
    classroom_id: int,
    db=Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Delete a classroom from the database. Restricted to administrators."""
    classroom_service.delete_classroom(db, id=classroom_id)
    return {"status": "ok", "message": f"Classroom with id {classroom_id} successfully deleted"}
