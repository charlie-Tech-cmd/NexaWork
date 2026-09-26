from app.models.branch import Branch


def create_test_branch(db_session, organization, region):
    branch = Branch(
        organization_id=organization.id,
        region_id=region.id,
        name="Test Branch",
        slug="test-branch",
        is_active=True,
    )

    db_session.add(branch)
    db_session.flush()

    return branch