"""Admin account seeding and initialization routine."""

import logging

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.security import hash_password
from app.db.models import User

logger = logging.getLogger(__name__)


def seed_admin_user(db: Session) -> None:
    """Ensure an administrator account exists based on environment configuration.

    Never prints or leaks password values.
    """
    settings = get_settings()

    admin_email = settings.admin_email.strip().lower()
    admin_password = settings.admin_password.strip()

    # Provide safe fallback credentials in development/test when not explicitly provided
    if not admin_email:
        if settings.app_env.lower() in ("development", "test"):
            admin_email = "admin@lumen.internal"
            admin_password = admin_password or "AdminSecretPass2026!#"
        else:
            logger.info("ADMIN_EMAIL not set; skipping automatic admin seeding in production.")
            return

    if len(admin_password) < 14:
        if settings.app_env.lower() == "production":
            raise ValueError("ADMIN_PASSWORD must be at least 14 characters in production.")
        admin_password = admin_password or "AdminSecretPass2026!#"

    existing_admin = db.query(User).filter(User.email == admin_email).first()
    if existing_admin:
        if settings.admin_reset:
            logger.info("ADMIN_RESET active: Updating credentials for admin user '%s'", admin_email)
            existing_admin.hashed_password = hash_password(admin_password)
            existing_admin.role = "admin"
            existing_admin.is_active = True
            db.commit()
        elif existing_admin.role != "admin":
            existing_admin.role = "admin"
            db.commit()
    else:
        logger.info("Seeding initial administrator account for '%s'", admin_email)
        admin_user = User(
            email=admin_email,
            hashed_password=hash_password(admin_password),
            role="admin",
            is_active=True,
            token_version=1,
        )
        db.add(admin_user)
        db.commit()
