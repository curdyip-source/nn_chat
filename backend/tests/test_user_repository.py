from app.repositories.users import UserRepository


def test_user_repository_create_and_list(db_session):
    repository = UserRepository(db_session)

    created = repository.create(
        {
            "user_login": "repo_user",
            "user_password": "hashed",
            "user_admin": False,
            "user_active": True,
            "user_first_name": "Repo",
            "user_second_name": "User",
            "user_age": 21,
            "user_address": "Repo Street",
        }
    )

    listed, total = repository.list()

    assert created.user_id is not None
    assert created.user_active is True
    assert created.user_created_at is not None
    assert total == 1
    assert any(user.user_login == "repo_user" for user in listed)


def test_user_repository_update(db_session, existing_user):
    repository = UserRepository(db_session)

    updated = repository.update(existing_user, {"user_first_name": "Updated"})

    assert updated.user_first_name == "Updated"


def test_user_repository_list_supports_search_and_pagination(db_session, existing_admin, existing_user):
    repository = UserRepository(db_session)

    items, total = repository.list(search="work", page=1, page_size=1, sort_by="user_login", sort_order="asc")

    assert total == 1
    assert len(items) == 1
    assert items[0].user_login == existing_user.user_login