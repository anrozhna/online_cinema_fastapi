from fastapi import APIRouter, Depends, status

from config.dependencies import require_admin
from schemas.accounts import UserGroupUpdateRequestSchema, UserGroupUpdateResponseSchema
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
