from pydantic import BaseModel, EmailStr, Field, field_validator

from database.models.accounts import UserGroupEnum
from database.validators import accounts as accounts_validators


class BaseEmailPasswordSchema(BaseModel):
    email: EmailStr = Field(
        ...,
        description="User's email address, used as the unique login identifier.",
        examples=["user@example.com"],
    )
    password: str = Field(
        ...,
        description=(
            "Must be at least 8 characters and include an uppercase letter, "
            "a lowercase letter, a digit, and a special character."
        ),
        examples=["StrongP@ssw0rd!"],
    )

    model_config = {"from_attributes": True}

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        return value.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        return accounts_validators.validate_password_strength(value)


class UserRegistrationRequestSchema(BaseEmailPasswordSchema):
    pass


class UserRegistrationResponseSchema(BaseModel):
    id: int = Field(..., description="Unique identifier of the newly created user.")
    email: EmailStr = Field(..., description="Email address the user registered with.")

    model_config = {"from_attributes": True}


class UserActivationRequestSchema(BaseModel):
    email: EmailStr = Field(
        ..., description="Email address of the account to activate."
    )
    token: str = Field(
        ...,
        description="Activation token sent to the user's email upon registration.",
    )


class MessageResponseSchema(BaseModel):
    message: str = Field(..., description="Human-readable result message.")


class UserActivationResendRequestSchema(BaseModel):
    email: EmailStr = Field(
        ...,
        description="Email address to resend the activation link to.",
    )


class UserLoginRequestSchema(BaseModel):
    email: EmailStr = Field(..., examples=["user@example.com"])
    password: str = Field(..., examples=["StrongP@ssw0rd!"])


class UserLoginResponseSchema(BaseModel):
    access_token: str = Field(
        ..., description="Short-lived JWT used to authenticate subsequent requests."
    )
    refresh_token: str = Field(
        ...,
        description="Long-lived token used to obtain a new access token via /refresh/.",
    )
    token_type: str = Field(
        default="bearer",
        description="Type of the access token, for use in the Authorization header.",
    )


class BaseRefreshTokenSchema(BaseModel):
    refresh_token: str = Field(..., description="A previously issued refresh token.")


class TokenRefreshRequestSchema(BaseRefreshTokenSchema):
    pass


class TokenRefreshResponseSchema(BaseModel):
    access_token: str = Field(..., description="Newly issued short-lived access token.")


class LogoutRequestSchema(BaseRefreshTokenSchema):
    pass


class PasswordChangeRequestSchema(BaseModel):
    old_password: str = Field(..., description="The user's current password.")
    new_password: str = Field(
        ...,
        description=(
            "Must be at least 8 characters and include an uppercase letter, "
            "a lowercase letter, a digit, and a special character. "
            "Must differ from the old password."
        ),
        examples=["EvenStr0ngerP@ss!"],
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        accounts_validators.validate_password_strength(value)
        return value


class PasswordResetRequestSchema(BaseModel):
    email: EmailStr = Field(
        ..., description="Email address to send password reset instructions to."
    )


class PasswordResetCompleteRequestSchema(BaseEmailPasswordSchema):
    token: str = Field(..., description="Password reset token received via email.")


class UserGroupUpdateRequestSchema(BaseModel):
    group: UserGroupEnum = Field(
        ..., description="The user group (role) to assign to the target user."
    )


class UserGroupUpdateResponseSchema(BaseModel):
    user_id: int = Field(..., description="ID of the user whose group was updated.")
    email: str = Field(..., description="Email address of the affected user.")
    group: UserGroupEnum = Field(..., description="The user's group after the update.")

    model_config = {"from_attributes": True}
