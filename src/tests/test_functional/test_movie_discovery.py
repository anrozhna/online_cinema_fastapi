from httpx import AsyncClient

from tests.conftest import create_movie


class TestMovieDiscoveryFlow:
    async def test_search_filter_sort_combined_scenario(
        self, client: AsyncClient, db_session, certification, director
    ):
        movie_a = await create_movie(
            db_session, certification, name="Inception", year=2010, imdb=8.8, price=9.99
        )
        movie_b = await create_movie(
            db_session,
            certification,
            name="Interstellar",
            year=2014,
            imdb=8.6,
            price=12.99,
        )
        await create_movie(
            db_session, certification, name="Titanic", year=1997, imdb=7.9, price=6.99
        )
        movie_a.directors.append(director)
        await db_session.commit()

        # 1. Full catalog has all three
        full_list = await client.get("/movies/")
        assert full_list.json()["total"] == 3

        # 2. Filter by year narrows to one
        by_year = await client.get("/movies/", params={"year": 1997})
        assert by_year.json()["total"] == 1
        assert by_year.json()["items"][0]["name"] == "Titanic"

        # 3. Filter by min_imdb excludes the lowest-rated movie
        by_imdb = await client.get("/movies/", params={"min_imdb": 8.0})
        assert by_imdb.json()["total"] == 2

        # 4. Search matches director name, not just title
        by_director = await client.get("/movies/", params={"search": director.name})
        assert by_director.json()["total"] == 1
        assert by_director.json()["items"][0]["name"] == "Inception"

        # 5. Sort by price ascending
        sorted_by_price = await client.get(
            "/movies/", params={"sort_by": "price", "sort_desc": False}
        )
        names_in_order = [item["name"] for item in sorted_by_price.json()["items"]]
        assert names_in_order == ["Titanic", "Inception", "Interstellar"]

        # 6. Pagination returns a partial page
        first_page = await client.get("/movies/", params={"limit": 2, "offset": 0})
        assert len(first_page.json()["items"]) == 2
        assert first_page.json()["total"] == 3

        # 7. Movie detail lookup by UUID from the list response
        detail_response = await client.get(f"/movies/{movie_b.uuid}/")
        assert detail_response.status_code == 200
        assert detail_response.json()["name"] == "Interstellar"
