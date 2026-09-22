from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.organizations import router as organizations_router
from app.api.routes.regions import router as regions_router
from app.api.routes.branches import router as branches_router
from app.api.routes.departments import router as departments_router
from app.api.routes.employees import router as employees_router
from app.core.config import settings
from app.api.routes.roles import router as roles_router
from app.api.routes.permissions import router as permissions_router
from app.api.routes.user_roles import router as user_roles_router
from app.api.routes.users import router as users_router
from app.api.routes.teams import router as teams_router


app = FastAPI(title=f"{settings.app_name} API")

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(organizations_router)
app.include_router(regions_router)
app.include_router(branches_router)
app.include_router(departments_router)
app.include_router(teams_router)
app.include_router(employees_router)
app.include_router(roles_router)
app.include_router(permissions_router)
app.include_router(user_roles_router)
app.include_router(users_router)


