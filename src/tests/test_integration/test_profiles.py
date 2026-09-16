import base64
import io

from httpx import AsyncClient

from database.models.accounts import User, UserProfile

MINIMAL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class TestGetProfile:
    async def test_get_profile_success(
        self,
        authenticated_client: AsyncClient,
        active_user: User,
        user_profile: UserProfile,
    ):
        response = await authenticated_client.get(
            f"/profiles/profile/{active_user.id}/"
        )

        assert response.status_code == 200
        body = response.json()
        assert body["user_id"] == active_user.id
        assert body["first_name"] == "Test"
        assert body["last_name"] == "User"

    async def test_get_profile_not_found_when_profile_missing(
        self, authenticated_client: AsyncClient, active_user: User
    ):
        response = await authenticated_client.get(
            f"/profiles/profile/{active_user.id}/"
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Profile not found."

    async def test_get_profile_forbidden_for_other_user(
        self, authenticated_client: AsyncClient, other_user: User
    ):
        response = await authenticated_client.get(f"/profiles/profile/{other_user.id}/")

        assert response.status_code == 403
        assert (
            response.json()["detail"]
            == "You don't have permission to edit this profile."
        )

    async def test_get_profile_requires_authentication(
        self, client: AsyncClient, active_user: User
    ):
        response = await client.get(f"/profiles/profile/{active_user.id}/")

        assert response.status_code == 401


class TestUpdateProfile:
    async def test_update_profile_text_fields_success(
        self,
        authenticated_client: AsyncClient,
        active_user: User,
        user_profile: UserProfile,
    ):
        response = await authenticated_client.patch(
            f"/profiles/profile/{active_user.id}/update/",
            data={"first_name": "Changed", "info": "Updated bio"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["first_name"] == "Changed"
        assert body["info"] == "Updated bio"
        assert body["last_name"] == "User"

    async def test_update_profile_not_found_when_profile_missing(
        self, authenticated_client: AsyncClient, active_user: User
    ):
        response = await authenticated_client.patch(
            f"/profiles/profile/{active_user.id}/update/",
            data={"first_name": "NewProfile"},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Profile not found."

    async def test_update_profile_with_avatar_uploads_via_storage(
        self,
        authenticated_client: AsyncClient,
        active_user: User,
        user_profile: UserProfile,
        fake_storage,
    ):
        avatar_file = io.BytesIO(MINIMAL_PNG)

        response = await authenticated_client.patch(
            f"/profiles/profile/{active_user.id}/update/",
            data={"first_name": "Test"},
            files={"avatar": ("avatar.png", avatar_file, "image/png")},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["avatar"] is not None
        assert f"{active_user.id}.png" in body["avatar"]
        assert f"avatars/{active_user.id}.png" in fake_storage.uploaded

    async def test_update_profile_avatar_upload_failure_returns_500(
        self,
        authenticated_client: AsyncClient,
        active_user: User,
        user_profile: UserProfile,
        fake_storage,
    ):
        fake_storage.should_fail = True
        avatar_file = io.BytesIO(MINIMAL_PNG)

        response = await authenticated_client.patch(
            f"/profiles/profile/{active_user.id}/update/",
            data={"first_name": "Test"},
            files={"avatar": ("avatar.png", avatar_file, "image/png")},
        )

        assert response.status_code == 500
        assert (
            response.json()["detail"]
            == "Failed to upload avatar. Please try again later."
        )

    async def test_update_profile_forbidden_for_other_user(
        self, authenticated_client: AsyncClient, other_user: User
    ):
        response = await authenticated_client.patch(
            f"/profiles/profile/{other_user.id}/update/",
            data={"first_name": "Hacker"},
        )

        assert response.status_code == 403

    async def test_update_profile_requires_authentication(
        self, client: AsyncClient, active_user: User
    ):
        response = await client.patch(
            f"/profiles/profile/{active_user.id}/update/",
            data={"first_name": "Hacker"},
        )

        assert response.status_code == 401
