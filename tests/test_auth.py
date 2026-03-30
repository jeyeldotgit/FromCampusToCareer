from __future__ import annotations


def test_register_student(client) -> None:
    response = client.post(
        "/auth/register",
        json={
            "email": "student@example.com",
            "password": "password123",
            "full_name": "Test Student",
            "role": "student",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "student@example.com"
    assert data["role"] == "student"
    assert "id" in data
    assert "hashed_password" not in data


def test_register_duplicate_email(client) -> None:
    payload = {
        "email": "dup@example.com",
        "password": "password123",
        "full_name": "Dup User",
        "role": "student",
    }
    r1 = client.post("/auth/register", json=payload)
    assert r1.status_code == 201

    r2 = client.post("/auth/register", json=payload)
    assert r2.status_code == 409


def test_register_invalid_role(client) -> None:
    response = client.post(
        "/auth/register",
        json={
            "email": "x@example.com",
            "password": "password123",
            "full_name": "X",
            "role": "superuser",
        },
    )
    assert response.status_code == 422


def test_register_short_password(client) -> None:
    response = client.post(
        "/auth/register",
        json={
            "email": "y@example.com",
            "password": "short",
            "full_name": "Y",
            "role": "student",
        },
    )
    assert response.status_code == 422


def test_login_success(client) -> None:
    client.post(
        "/auth/register",
        json={
            "email": "login@example.com",
            "password": "password123",
            "full_name": "Login User",
            "role": "student",
        },
    )
    response = client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "student"


def test_login_wrong_password(client) -> None:
    client.post(
        "/auth/register",
        json={
            "email": "loginwrong@example.com",
            "password": "password123",
            "full_name": "User",
            "role": "student",
        },
    )
    response = client.post(
        "/auth/login",
        json={"email": "loginwrong@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_login_nonexistent_user(client) -> None:
    response = client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "password123"},
    )
    assert response.status_code == 401
