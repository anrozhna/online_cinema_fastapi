from fastapi import APIRouter, status

from config.dependencies import CurrentUser
from schemas.accounts import (
    LogoutRequestSchema,
    MessageResponseSchema,
    PasswordChangeRequestSchema,
    PasswordResetCompleteRequestSchema,
    PasswordResetRequestSchema,
    TokenRefreshRequestSchema,
    TokenRefreshResponseSchema,
    UserActivationRequestSchema,
    UserActivationResendRequestSchema,
    UserLoginRequestSchema,
    UserLoginResponseSchema,
    UserRegistrationRequestSchema,
    UserRegistrationResponseSchema,
)
from services.accounts import AccountServiceDep

router = APIRouter()


@router.post(
    path="/register/",
    response_model=UserRegistrationResponseSchema,
    summary="User Registration",
    description="Register a new user with an email and password.",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "User registered successfully."},
        409: {"description": "User with this email already exists."},
        500: {"description": "An error occurred during user creation."},
    },
)
async def register_user(
    user_data: UserRegistrationRequestSchema,
    account_service: AccountServiceDep,
):
    return await account_service.register_user(user_data=user_data)


@router.post(
    path="/activate/",
    response_model=MessageResponseSchema,
    summary="Activate user account",
    description="Activate a user's account using their email and activation token.",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "The user's account was successfully activated."},
        400: {
            "description": "Activation token is invalid or expired, "
            "or account is already active."
        },
    },
)
async def activate_account(
    activation_data: UserActivationRequestSchema,
    account_service: AccountServiceDep,
):
    return await account_service.activate_account(activation_data=activation_data)


@router.post(
    path="/activate/resend-link/",
    response_model=MessageResponseSchema,
    summary="Resend activation email",
    description="Resend the activation email to a user's email address.",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "The activation email was successfully resent."},
        404: {"description": "User is not found."},
    },
)
async def resend_activation_link(
    request_data: UserActivationResendRequestSchema,
    account_service: AccountServiceDep,
):
    return await account_service.resend_activation_link(request_data=request_data)


@router.post(
    path="/login/",
    response_model=UserLoginResponseSchema,
    summary="Login a user",
    description="Authenticate a user and return access and refresh tokens.",
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Invalid email or password."},
        403: {"description": "User account is not activated."},
        500: {"description": "An error occurred while processing the request."},
    },
)
async def login(
    login_data: UserLoginRequestSchema,
    account_service: AccountServiceDep,
):
    return await account_service.login(login_data=login_data)


@router.post(
    path="/refresh/",
    response_model=TokenRefreshResponseSchema,
    summary="Refresh access token",
    description="Refresh access token using refresh token",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Access token successfully refreshed."},
        400: {"description": "The provided refresh token is invalid or expired."},
        401: {
            "description": "The provided refresh token does not exist in the database."
        },
        404: {
            "description": "The user associated with the refresh token does not exist."
        },
    },
)
async def refresh_access_token(
    token_data: TokenRefreshRequestSchema,
    account_service: AccountServiceDep,
):
    return await account_service.refresh_access_token(token_data=token_data)


@router.post(
    path="/logout/",
    response_model=MessageResponseSchema,
    summary="Logout",
    description="Logout the user by invalidating the refresh token.",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "User logged out successfully.",
        },
        401: {
            "description": "Invalid refresh token.",
        },
    },
)
async def logout(
    logout_data: LogoutRequestSchema,
    account_service: AccountServiceDep,
):
    return await account_service.logout(logout_data=logout_data)


@router.post(
    path="/change-password/",
    response_model=MessageResponseSchema,
    summary="Change password",
    description="Change the password for the currently authenticated user.",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Password changed successfully.",
        },
        401: {
            "description": "Invalid or missing access token, or wrong old password.",
        },
        422: {
            "description": "New password does not meet strength requirements, "
            "or matches the old password."
        },
    },
)
async def change_password(
    password_data: PasswordChangeRequestSchema,
    current_user: CurrentUser,
    account_service: AccountServiceDep,
):
    return await account_service.change_password(
        password_data=password_data, current_user=current_user
    )


@router.post(
    path="/password-reset/request/",
    response_model=MessageResponseSchema,
    summary="Request Password Reset Token",
    description=(
        "Allows a user to request a password reset token. "
        "If the user exists and is active, a new token will be generated "
        "and any existing tokens will be invalidated."
    ),
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "The request was successful. This response is always "
            "returned regardless of the user's existence or status."
        },
    },
)
async def request_password_reset_token(
    data: PasswordResetRequestSchema,
    account_service: AccountServiceDep,
):
    return await account_service.request_password_reset_token(data=data)


@router.post(
    path="/password-reset/complete/",
    response_model=MessageResponseSchema,
    summary="Complete Password Reset",
    description="Reset a user's password if a valid token is provided.",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Password reset successfully."},
        400: {
            "description": "The provided email, token, or password is invalid, "
            "or the token has expired."
        },
        500: {
            "description": "An unexpected error occurred while resetting the password."
        },
    },
)
async def reset_password(
    data: PasswordResetCompleteRequestSchema,
    account_service: AccountServiceDep,
):
    return await account_service.reset_password(data=data)
