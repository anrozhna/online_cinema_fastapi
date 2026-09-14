from datetime import date

from fastapi import File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, HttpUrl, ValidationError, field_validator

from validation.profile import (
    validate_birth_date,
    validate_gender,
    validate_image,
    validate_name,
)


class UserProfileBaseSchema(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    gender: str | None = None
    date_of_birth: date | None = None
    info: str | None = None


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
        first_name: str | None = Form(None),
        last_name: str | None = Form(None),
        gender: str | None = Form(None),
        date_of_birth: date | None = Form(None),
        info: str | None = Form(None),
        avatar: UploadFile | None = File(None),
    ) -> "UserProfileRequestSchema":
        try:
            return cls(
                first_name=first_name,
                last_name=last_name,
                gender=gender,
                date_of_birth=date_of_birth,
                info=info,
                avatar=avatar,
            )
        except ValidationError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
            )


class UserProfileResponseSchema(UserProfileBaseSchema):
    id: int
    user_id: int
    avatar: HttpUrl | None = None

    model_config = {"from_attributes": True}
