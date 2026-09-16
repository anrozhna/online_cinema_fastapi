from httpx import AsyncClient

from database.models.accounts import User


class TestChangeUserGroup:
    async def test_admin_can_promote_user_to_moderator(
        self,
        authenticated_admin_client: AsyncClient,
        active_user: User,
        moderator_group,
    ):
        response = await authenticated_admin_client.patch(
            f"/admin/users/{active_user.id}/group/",
            json={"group": "moderator"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["user_id"] == active_user.id
        assert body["email"] == active_user.email
        assert body["group"] == "moderator"

    async def test_admin_can_demote_user_back_to_user_group(
        self,
        authenticated_admin_client: AsyncClient,
        active_user: User,
        moderator_group,
        user_group,
    ):
        # promote first
        await authenticated_admin_client.patch(
            f"/admin/users/{active_user.id}/group/",
            json={"group": "moderator"},
        )
        # then demote back
        response = await authenticated_admin_client.patch(
            f"/admin/users/{active_user.id}/group/",
            json={"group": "user"},
        )

        assert response.status_code == 200
        assert response.json()["group"] == "user"

    async def test_change_group_requires_admin(
        self, authenticated_client: AsyncClient, other_user: User, moderator_group
    ):
        # authenticated_client is a regular (non-admin) user
        response = await authenticated_client.patch(
            f"/admin/users/{other_user.id}/group/",
            json={"group": "moderator"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Admin privileges required."

    async def test_change_group_requires_authentication(
        self, client: AsyncClient, active_user: User, moderator_group
    ):
        response = await client.patch(
            f"/admin/users/{active_user.id}/group/",
            json={"group": "moderator"},
        )

        assert response.status_code == 401

    async def test_change_group_not_found_for_missing_user(
        self, authenticated_admin_client: AsyncClient, moderator_group
    ):
        response = await authenticated_admin_client.patch(
            "/admin/users/999999/group/",
            json={"group": "moderator"},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found or not active."

    async def test_change_group_not_found_for_inactive_user(
        self,
        authenticated_admin_client: AsyncClient,
        db_session,
        user_group,
        moderator_group,
    ):
        from database.models.accounts import User as UserModel

        inactive_user = UserModel.create(
            email="inactive@example.com",
            raw_password="StrongP@ssw0rd!",
            group_id=user_group.id,
        )
        # is_active defaults to False per User.create — left untouched intentionally
        db_session.add(inactive_user)
        await db_session.commit()
        await db_session.refresh(inactive_user)

        response = await authenticated_admin_client.patch(
            f"/admin/users/{inactive_user.id}/group/",
            json={"group": "moderator"},
        )

        assert response.status_code == 404

    async def test_change_group_rejects_invalid_group_value(
        self, authenticated_admin_client: AsyncClient, active_user: User
    ):
        response = await authenticated_admin_client.patch(
            f"/admin/users/{active_user.id}/group/",
            json={"group": "superadmin"},  # not a valid UserGroupEnum member
        )

        assert response.status_code == 422

    async def test_change_group_500_when_target_group_not_seeded(
        self, authenticated_admin_client: AsyncClient, active_user: User
    ):
        # No moderator_group fixture used here -> that UserGroup row doesn't exist in DB
        response = await authenticated_admin_client.patch(
            f"/admin/users/{active_user.id}/group/",
            json={"group": "moderator"},
        )

        assert response.status_code == 500
        assert response.json()["detail"] == "Requested user group is not configured."
