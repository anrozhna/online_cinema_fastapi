from fastapi import APIRouter, Depends, status

from config.dependencies import verify_profile_owner
from schemas.profiles import UserProfileRequestSchema, UserProfileResponseSchema
from services.profiles import ProfileServiceDep

router = APIRouter()


@router.get(
    path="/profile/{user_id}/",
    response_model=UserProfileResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Get user profile",
    description=(
        "Retrieve the profile for the specified user, including personal "
        "information and an avatar image. "
        "Only the profile owner may perform this action."
    ),
    responses={
        200: {"description": "Profile retrieved."},
        403: {"description": "You don't have permission to view this profile."},
        404: {"description": "User not found or not active."},
    },
    dependencies=[Depends(verify_profile_owner)],
)
async def get_profile(user_id: int, profile_service: ProfileServiceDep):
    return await profile_service.get_profile(user_id=user_id)


@router.patch(
    path="/profile/{user_id}/update/",
    response_model=UserProfileResponseSchema,
    summary="Update user profile",
    description=(
        "Partially update the profile for the specified user — only the fields "
        "provided in the form are changed; omitted fields keep their current "
        "values. Only the profile owner may perform this action."
    ),
    responses={
        200: {"description": "Profile successfully updated."},
        403: {"description": "You don't have permission to edit this profile."},
        404: {"description": "User not found or not active."},
        422: {"description": "Invalid profile data or avatar image."},
        500: {"description": "Failed to upload avatar. Please try again later."},
    },
    dependencies=[Depends(verify_profile_owner)],
)
async def update_profile(
    user_id: int,
    profile_service: ProfileServiceDep,
    profile_data: UserProfileRequestSchema = Depends(UserProfileRequestSchema.as_form),
):
    return await profile_service.update_profile(
        user_id=user_id, profile_data=profile_data
    )
