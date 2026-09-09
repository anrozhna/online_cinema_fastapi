import enum

from sqlalchemy import Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base


class UserGroupEnum(str, enum.Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class GenderEnum(str, enum.Enum):
    MAN = "man"
    WOMAN = "woman"


class UserGroup(Base):
    __tablename__ = "user_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[UserGroupEnum] = mapped_column(
        Enum(UserGroupEnum), nullable=False, unique=True
    )

    users: Mapped[list["User"]] = relationship("User", back_populates="group")

    def __repr__(self):
        return f"<UserGroup(id={self.id}, name={self.name})>"
