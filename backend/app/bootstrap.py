from __future__ import annotations

import os
from datetime import date
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import Organization, OrganizationMember, User
from .security import hash_password

DEMO_PASSWORD = "VolgaDemo1"


def ensure_admin(db: Session) -> None:
    """Создаёт первого администратора из окружения, если администраторов ещё нет."""
    if db.query(User).filter(User.role == "admin").first() is not None:
        return
    email = os.getenv("ADMIN_EMAIL", "").lower().strip()
    password = os.getenv("ADMIN_PASSWORD", "")
    username = os.getenv("ADMIN_USERNAME", "admin").strip()
    if not email or len(password) < 6 or not username:
        return
    existing = db.query(User).filter(User.email == email).first()
    if existing is not None:
        existing.role = "admin"
        db.commit()
        return
    taken = db.query(User).filter(func.lower(User.username) == username.lower()).first()
    if taken is not None:
        return
    db.add(User(username=username, email=email, password_hash=hash_password(password), role="admin"))
    db.commit()


def _demo_user(
    db: Session,
    username: str,
    email: str,
    role: str,
    full_name: Optional[str] = None,
    birth_date: Optional[date] = None,
) -> Optional[User]:
    existing = db.query(User).filter(User.email == email).first()
    if existing is not None:
        return existing
    taken = db.query(User).filter(func.lower(User.username) == username.lower()).first()
    if taken is not None:
        return None
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(DEMO_PASSWORD),
        role=role,
        full_name=full_name,
        birth_date=birth_date,
    )
    db.add(user)
    db.flush()
    return user


def ensure_demo_accounts(db: Session) -> None:
    """Создаёт демо-входы участника, организации и администратора, если их ещё нет."""
    if os.getenv("DEMO_ACCOUNTS", "1") == "0":
        return
    _demo_user(
        db,
        "demo_player",
        "demo.player@example.com",
        "participant",
        full_name="Иван Петров",
        birth_date=date(2006, 3, 15),
    )
    company = _demo_user(db, "demo_company", "demo.company@example.com", "participant", full_name="Мария Соколова")
    if company is not None:
        name = "Демо ВолгаКод"
        names = [row[0] for row in db.query(Organization.name).all()]
        if not any(current.casefold() == name.casefold() for current in names):
            organization = Organization(
                name=name,
                description="Демонстрационная организация для просмотра кабинета компании.",
                created_by_id=company.id,
            )
            db.add(organization)
            db.flush()
            db.add(OrganizationMember(organization_id=organization.id, user_id=company.id, member_role="owner"))
    if db.query(User).filter(User.role == "admin").first() is None:
        _demo_user(db, "demo_admin", "demo.admin@example.com", "admin", full_name="Администратор демо")
    db.commit()
