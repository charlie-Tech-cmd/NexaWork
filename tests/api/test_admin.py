def test_admin_dashboard_requires_admin_access(
    client,
):
    response = client.get(
        "/api/v1/admin/dashboard"
    )

    assert response.status_code == 401