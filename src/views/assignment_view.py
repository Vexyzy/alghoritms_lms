from exceptions.AssignmentException import (
    AssignmentNotFoundException,
    AssignmentException,
    AssignmentGameFieldException,
    AssignmentPositionError,
    AssignmentElementFieldError,
)
from exceptions.CourseException import CourseNotFoundException
from exceptions.ValidationException import UUIDValidationException
from fastapi import APIRouter, HTTPException, Depends, Request, Body
from typing import List

from repository.assignment_repo import AssignmentRepo
from repository.user_repo import UserRepository
from schemas.action_schema import ActionGet

# schemas of course
from schemas.assignment_schema import (
    AssignmentGet,
    AssignmentCreate,
)

from db.db_helper import db_helper
from schemas.game_element_schema import GameElementGet, GameElementCreate
from services.assignments_sevices import AssignmentsService

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError


# Auth library
# ----------------------
# import auth settings
from core.config import AUTH_CONFIG

# for auth working
from authx import AuthX

# ----------------------

# logger
from logger.logger_module import ModuleLoger

# path worker
from pathlib import Path

from starlette.responses import Response

from services.user_services import UserService

# utils that check permissions
from utils.user_utils.user_utils import only_teacher


logger = ModuleLoger(Path(__file__).stem)

security = AuthX(config=AUTH_CONFIG)
router = APIRouter(tags=["Assignment"])


@router.get(
    "/assignments/",
    response_model=List[AssignmentGet],
    dependencies=[
        Depends(security.access_token_required),
    ],
)
async def get_assignments(
    response: Response,
    course_uuid: str,
    session: AsyncSession = Depends(db_helper.session_dependency),
) -> list[AssignmentGet]:
    try:
        logger.info("Try to get all assignments of course %s" % course_uuid)
        assignments = await AssignmentsService.get_course_assignments(
            course_uuid=course_uuid, session=session
        )
    except SQLAlchemyError as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Database error")

    except UUIDValidationException:
        logger.info("Ask assigment with invalid course uuid: %s" % course_uuid)
        raise HTTPException(
            status_code=400,
            detail="UUID of course validation error. UUID should be 32..36 "
            "length and UUID must contains only hex symbols.",
        )
    if assignments:
        logger.info(
            "Success trying of getting assignments of course %s. "
            "Found %s assignments" % (course_uuid, len(assignments))
        )
        response.status_code = 201
        return assignments

    logger.info(
        "Fail of getting assignments for course %s. Assignments doesn't exists"
        % course_uuid
    )
    raise HTTPException(
        status_code=404,
        detail="Assignment not found",
    )


@router.post(
    path="/assignment/",
)
async def create_assignment(
    assignment_in: AssignmentCreate,
    request: Request,
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    await only_teacher(request)
    try:
        logger.info("Try to create assignment with data %s" % assignment_in)
        assignment = await AssignmentsService.create_assignment(
            assignment_in=assignment_in, session=session
        )
    except UUIDValidationException:
        logger.info(
            "Failed to create assignment with course uuid: %s"
            % assignment_in.course_id
        )
        raise HTTPException(
            status_code=400,
            detail="UUID of course validation error. UUID should be 32..36 "
            "length and UUID must contains only hex symbols.",
        )
    except CourseNotFoundException:
        logger.info(
            "Failed to create assignment with doesn't existing course uuid: %s"
            % assignment_in.course_id
        )
        raise HTTPException(
            status_code=400,
            detail=f"Course with id {assignment_in.course_id} not found, "
            f"can't create assignment",
        )
    except AssignmentGameFieldException as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except AssignmentPositionError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except SQLAlchemyError as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Database error")

    if assignment:
        return assignment

    logger.error("Assignment ( %s ) not created" % assignment_in)
    raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/assignment/delete/{assignment_id}",
)
async def delete_assignment(
    assignment_uuid: str,
    response: Response,
    request: Request,
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    await only_teacher(request)
    try:
        logger.info("Try to delete assignment with uuid %s" % assignment_uuid)
        assignment = await AssignmentsService.delete_assignment(
            assignment_uuid=assignment_uuid, session=session
        )
    except SQLAlchemyError as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Database error")
    except UUIDValidationException:
        logger.info(
            args="Failed to delete assignment with invalid uuid %s"
            % assignment_uuid
        )
        raise HTTPException(
            status_code=400,
            detail="UUID of course validation error. UUID should be 32..36 "
            "length and UUID must contains only hex symbols.",
        )
    except AssignmentNotFoundException:
        logger.info(
            "Failed to delete assignment with uuid %s. Assignment not found"
            % assignment_uuid
        )
        raise HTTPException(
            status_code=404,
            detail=f"Assignment with id {assignment_uuid} not found",
        )
    except AssignmentException as e:
        logger.error(e)
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )

    if assignment:
        response.status_code = 201
        logger.info(
            "Successfully deleted assignment with uuid %s" % assignment_uuid
        )
        return {
            "detail": f"Assigment with id"
            f" {assignment.assignment_id} successfully deleted"
        }

    logger.info("Failed to delete assignment with uuid" % assignment_uuid)
    raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/full_assignment/{assignment_uuid}",
    response_model=tuple[AssignmentGet, tuple[GameElementGet, ...] | None],
)
async def get_total_info_assignment(
    assignment_uuid: str,
    session: AsyncSession = Depends(db_helper.session_dependency),
) -> tuple[AssignmentGet, tuple[GameElementGet, ...] | None]:
    pass
    try:
        data = await AssignmentsService.total_info_about_assignment(
            assignment_uuid=assignment_uuid, session=session
        )

        if data:
            assignment, elements = data
            return assignment, elements

        raise HTTPException(status_code=404, detail="Assignment not found")

    except SQLAlchemyError as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Database error")
    except UUIDValidationException:
        logger.info(
            args="Failed to delete assignment with invalid uuid %s"
            % assignment_uuid
        )
        raise HTTPException(
            status_code=400,
            detail="UUID of course validation error. UUID should be 32..36 "
            "length and UUID must contains only hex symbols.",
        )
    except AssignmentNotFoundException:
        logger.info(
            "Failed to delete assignment with uuid %s. Assignment not found"
            % assignment_uuid
        )
        raise HTTPException(
            status_code=404,
            detail=f"Assignment with id {assignment_uuid} not found",
        )
    except AssignmentException as e:
        logger.error(e)
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )


@router.post("/add_elements/")
async def add_elements(
    element_list: list[GameElementCreate, ...],
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    try:
        return await AssignmentsService.add_elements(
            element_list=element_list,
            session=session,
        )
    except AssignmentElementFieldError:
        raise HTTPException(
            status_code=400,
            detail="You cannot add this elements. "
            "Some of them go beyond the limits of the "
            "playing field or are placed on already occupied squares. "
            "Or assignment doesn't exist.",
        )


@router.get("/actions/{assignment_uuid}/")
async def get_actions(
    assignment_uuid: str,
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    # TODO: create service and exceptions
    return await AssignmentRepo.get_assignment_actions(
        action_uuid=assignment_uuid,
        session=session,
    )


@router.post("/add_actions/")
async def add_actions(
    actions_id: list[int, ...] = Body(),
    assignment_uuid: str = Body(),
    session: AsyncSession = Depends(db_helper.session_dependency),
):
    # TODO: create service and exceptions
    return await AssignmentRepo.add_actions(
        actions_id=actions_id,
        assignment_uuid=assignment_uuid,
        session=session,
    )
