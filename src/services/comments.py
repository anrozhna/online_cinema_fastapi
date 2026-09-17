from typing import Annotated

from fastapi import Depends, HTTPException, status

from config.dependencies import CommentRepo, MovieRepo
from database.models.movies import Comment
from schemas.movies import CommentCreateRequestSchema, CommentResponseSchema
from services.movies_shared import get_movie_or_404


class CommentService:
    def __init__(self, comment_repo: CommentRepo, movie_repo: MovieRepo):
        self.comment_repo = comment_repo
        self.movie_repo = movie_repo

    @staticmethod
    def _build_comment_tree(comments: list[Comment]) -> list[CommentResponseSchema]:
        """Build a nested reply tree from a FLAT list of comments in O(n),
        without touching the (potentially unloaded) `replies` relationship
        on any ORM object — avoids the async lazy-load / MissingGreenlet
        problem entirely by working from plain data, not ORM attributes."""
        schemas_by_id: dict[int, CommentResponseSchema] = {
            comment.id: CommentResponseSchema.model_validate(comment)
            for comment in comments
        }

        roots: list[CommentResponseSchema] = []
        for comment in comments:
            schema = schemas_by_id[comment.id]
            if comment.parent_comment_id is None:
                roots.append(schema)
            else:
                parent_schema = schemas_by_id.get(comment.parent_comment_id)
                if parent_schema is not None:
                    parent_schema.replies.append(schema)

        return roots

    async def list_comments_for_movie(
        self, movie_id: int
    ) -> list[CommentResponseSchema]:
        await get_movie_or_404(self.movie_repo, movie_id)

        comments = await self.comment_repo.list_by_movie(movie_id)
        return self._build_comment_tree(comments)

    async def create_comment(
        self, movie_id: int, user_id: int, data: CommentCreateRequestSchema
    ) -> CommentResponseSchema:
        await get_movie_or_404(self.movie_repo, movie_id)

        if data.parent_comment_id is not None:
            parent = await self.comment_repo.get_by_id(data.parent_comment_id)
            if parent is None or parent.movie_id != movie_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent comment not found for this movie.",
                )

        comment = Comment(
            user_id=user_id,
            movie_id=movie_id,
            text=data.text,
            parent_comment_id=data.parent_comment_id,
        )
        self.comment_repo.add(comment)
        await self.comment_repo.db.commit()
        await self.comment_repo.db.refresh(comment)

        return CommentResponseSchema.model_validate(comment)


CommentServiceDep = Annotated[CommentService, Depends()]
