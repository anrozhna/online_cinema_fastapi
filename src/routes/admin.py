from fastapi import APIRouter, Depends, status

from config.dependencies import require_admin
from schemas.accounts import (
    MessageResponseSchema,
    UserGroupUpdateRequestSchema,
    UserGroupUpdateResponseSchema,
)
from services.accounts import AccountServiceDep

router = APIRouter(dependencies=[Depends(require_admin)])


@router.patch(
    path="/users/{user_id}/group/",
    response_model=UserGroupUpdateResponseSchema,
    summary="Change a user's group",
    description="Assign a new user group (role) to the specified user.",
    status_code=status.HTTP_200_OK,
    responses={
        403: {"description": "Admin privileges required."},
        404: {"description": "User not found or not active."},
        500: {"description": "An error occurred while updating the user group."},
    },
)
async def change_user_group(
    user_id: int,
    group_data: UserGroupUpdateRequestSchema,
    account_service: AccountServiceDep,
):
    return await account_service.change_user_group(
        user_id=user_id, group_data=group_data
    )


@router.post(
    path="/users/{user_id}/activate/",
    response_model=MessageResponseSchema,
    summary="Manually activate a user account",
    description="Activate a user's account directly, bypassing the email token flow.",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "User account is already active."},
        403: {"description": "Admin privileges required."},
        404: {"description": "User not found."},
        500: {"description": "An error occurred while activating the user."},
    },
)
async def activate_user_manually(user_id: int, account_service: AccountServiceDep):
    return await account_service.activate_user_manually(user_id=user_id)
