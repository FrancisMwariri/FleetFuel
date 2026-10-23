import os
from argparse import ArgumentParser
from uuid import uuid4

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import get_session_factory
from app.models.entities import Organization, User


def bootstrap_admin() -> None:
    email = os.environ["FLEETFUEL_BOOTSTRAP_ADMIN_EMAIL"].strip().lower()
    password = os.environ["FLEETFUEL_BOOTSTRAP_ADMIN_PASSWORD"]
    organization_name = os.environ["FLEETFUEL_BOOTSTRAP_ORGANIZATION"]
    currency = os.environ["FLEETFUEL_BOOTSTRAP_CURRENCY"].upper()
    if len(password) < 12:
        raise ValueError("Bootstrap administrator password must be at least 12 characters")

    factory = get_session_factory()
    with factory.begin() as session:
        existing_admin = session.scalar(select(User).where(User.email == email))
        if existing_admin is not None:
            if existing_admin.role == "ORG_ADMIN" and existing_admin.organization_id is not None:
                print("Organization administrator already exists; bootstrap skipped")
                return
            if existing_admin.role != "SUPER_ADMIN" or existing_admin.organization_id is not None:
                raise RuntimeError(
                    "Bootstrap email belongs to an account that cannot be converted "
                    "to an organization administrator"
                )
        elif session.scalar(select(User.id).limit(1)) is not None:
            raise RuntimeError("Bootstrap is only allowed when no users exist")
        organization = Organization(
            name=organization_name,
            slug=f"bootstrap-{uuid4().hex[:12]}",
            default_currency=currency,
        )
        session.add(organization)
        session.flush()
        if existing_admin is not None:
            existing_admin.organization_id = organization.id
            existing_admin.role = "ORG_ADMIN"
            print("Platform administrator assigned to the bootstrap fleet")
        else:
            session.add(
                User(
                    organization_id=organization.id,
                    email=email,
                    password_hash=hash_password(password),
                    full_name="Platform Administrator",
                    role="ORG_ADMIN",
                )
            )


def bootstrap_super_admin() -> None:
    email = os.environ["FLEETFUEL_BOOTSTRAP_ADMIN_EMAIL"].strip().lower()
    password = os.environ["FLEETFUEL_BOOTSTRAP_ADMIN_PASSWORD"]
    if len(password) < 12:
        raise ValueError("Bootstrap administrator password must be at least 12 characters")
    factory = get_session_factory()
    with factory.begin() as session:
        existing = session.scalar(
            select(User).where(User.role == "SUPER_ADMIN").limit(1)
        )
        if existing is not None:
            if existing.email != email:
                raise RuntimeError("A different platform administrator already exists")
            print("Platform administrator already exists; bootstrap skipped")
            return
        session.add(
            User(
                organization_id=None,
                email=email,
                password_hash=hash_password(password),
                full_name="Platform Administrator",
                role="SUPER_ADMIN",
            )
        )


def main() -> None:
    parser = ArgumentParser(prog="fleetfuel")
    parser.add_argument("command", choices=["bootstrap-admin", "bootstrap-super-admin"])
    args = parser.parse_args()
    if args.command == "bootstrap-admin":
        bootstrap_admin()
    elif args.command == "bootstrap-super-admin":
        bootstrap_super_admin()


if __name__ == "__main__":
    main()
