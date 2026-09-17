from pydantic import BaseModel


class GenreBaseSchema(BaseModel):
    name: str


class GenreResponseSchema(GenreBaseSchema):
    id: int

    model_config = {"from_attributes": True}


class StarBaseSchema(BaseModel):
    name: str


class StarResponseSchema(StarBaseSchema):
    id: int

    model_config = {"from_attributes": True}


class DirectorBaseSchema(BaseModel):
    name: str


class DirectorResponseSchema(DirectorBaseSchema):
    id: int

    model_config = {"from_attributes": True}


class CertificationBaseSchema(BaseModel):
    name: str


class CertificationResponseSchema(CertificationBaseSchema):
    id: int

    model_config = {"from_attributes": True}
