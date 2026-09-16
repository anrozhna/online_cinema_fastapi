from datetime import date

from fastapi import File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field, HttpUrl, ValidationError, field_validator

from validation.profile import (
    validate_birth_date,
    validate_gender,
    validate_image,
    validate_name,
)


class UserProfileBaseSchema(BaseModel):
    first_name: str | None = Field(
        default=None,
        description="User's first name. Letters only.",
        examples=["John"],
    )
    last_name: str | None = Field(
        default=None,
        description="User's last name. Letters only.",
        examples=["Smith"],
    )
    gender: str | None = Field(
        default=None,
        description="User's gender identity.",
        examples=["woman"],
    )
    date_of_birth: date | None = Field(
        default=None,
        description="User's date of birth. Must correspond to an age of 18 or older.",
        examples=["1995-06-15"],
    )
    info: str | None = Field(
        default=None,
        description="Short free-text bio or description.",
        examples=["Movie enthusiast and weekend hiker."],
    )


class UserProfileRequestSchema(UserProfileBaseSchema):
    avatar: UploadFile | None = None

    model_config = {"arbitrary_types_allowed": True}

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_first_and_last_name(cls, value: str) -> str:
        try:
            validate_name(value)
        except ValueError as error:
            raise ValueError(str(error))
        return value

    @field_validator("avatar")
    @classmethod
    def validate_avatar(cls, value: UploadFile) -> UploadFile:
        try:
            validate_image(value)
        except ValueError as error:
            raise ValueError(str(error))
        return value

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, value: str) -> str:
        try:
            validate_gender(value)
        except ValueError as error:
            raise ValueError(str(error))
        return value

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, value: date) -> date:
        try:
            validate_birth_date(value)
        except ValueError as error:
            raise ValueError(str(error))
        return value

    @classmethod
    def as_form(
        cls,
        first_name: str | None = Form(
            None, description="User's first name. Letters only."
        ),
        last_name: str | None = Form(
            None, description="User's last name. Letters only."
        ),
        gender: str | None = Form(None, description="User's gender identity."),
        date_of_birth: date | None = Form(
            None,
            description="User's date of birth. "
            "Must correspond to an age of 18 or older.",
        ),
        info: str | None = Form(
            None, description="Short free-text bio or description."
        ),
        avatar: UploadFile | None = File(
            None,
            description=(
                "Profile picture. JPG, JPEG, or PNG, max 1 MB. "
                "Omit this field to leave the current avatar unchanged."
            ),
        ),
    ) -> "UserProfileRequestSchema":
        raw_data = {
            "first_name": first_name,
            "last_name": last_name,
            "gender": gender,
            "date_of_birth": date_of_birth,
            "info": info,
            "avatar": avatar,
        }
        # Only pass fields the client actually sent — anything left as None here
        # (i.e. omitted from the multipart form) must stay untouched by PATCH,
        # not be explicitly set to None on the model.
        provided_data = {
            key: value for key, value in raw_data.items() if value is not None
        }

        try:
            # mypy can't verify **kwargs against named Pydantic fields
            return cls(**provided_data)  # type: ignore[arg-type]
        except ValidationError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
            )


class UserProfileResponseSchema(UserProfileBaseSchema):
    id: int = Field(..., description="Unique identifier of the profile.")
    user_id: int = Field(..., description="ID of the user this profile belongs to.")
    avatar: HttpUrl | None = Field(
        default=None, description="Public URL of the user's avatar image, if uploaded."
    )

    model_config = {"from_attributes": True}
