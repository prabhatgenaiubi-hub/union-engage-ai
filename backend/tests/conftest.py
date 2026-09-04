import os
os.environ["DATABASE_URL"]="sqlite:///./test.db"
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.base import Base
from app.db.session import engine,SessionLocal
from app.models import Customer,User
from app.core.security import hash_password
@pytest.fixture(autouse=True)
def database():
 Base.metadata.drop_all(engine); Base.metadata.create_all(engine); db=SessionLocal(); c=Customer(customer_code="T001",name="Test User",city="Pune",relationship_since="2024"); db.add(c); db.flush(); db.add(User(login_id="T001",password_hash=hash_password("Demo@123"),user_type="customer",role="customer",display_name="Test User",customer_id=c.id)); db.add(User(login_id="ADMIN",password_hash=hash_password("Demo@123"),user_type="employee",role="admin",display_name="Admin")); db.commit(); db.close(); yield
@pytest.fixture
def client(): return TestClient(app)
@pytest.fixture
def customer_headers(client):
 token=client.post("/api/auth/customer/login",json={"login_id":"T001","password":"Demo@123"}).json()["access_token"]; return {"Authorization":f"Bearer {token}"}
@pytest.fixture
def admin_headers(client):
 token=client.post("/api/auth/employee/login",json={"login_id":"ADMIN","password":"Demo@123"}).json()["access_token"]; return {"Authorization":f"Bearer {token}"}
