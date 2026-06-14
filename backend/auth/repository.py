from uuid import UUID

from sqlalchemy.orm import Session

from auth.passwords import hash_password
from db.models import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: UUID) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email.lower()).first()

    def get_by_facebook_id(self, facebook_id: str) -> User | None:
        return self.db.query(User).filter(User.facebook_id == facebook_id).first()

    def create_email_user(self, *, email: str, password: str, name: str) -> User:
        user = User(
            email=email.lower(),
            password_hash=hash_password(password),
            name=name.strip() or email.split("@")[0],
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def create_facebook_user(
        self,
        *,
        facebook_id: str,
        email: str | None,
        name: str,
        avatar_url: str | None,
    ) -> User:
        user = User(
            facebook_id=facebook_id,
            email=email.lower() if email else None,
            name=name.strip() or "Facebook User",
            avatar_url=avatar_url,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def link_facebook(self, user: User, *, facebook_id: str, avatar_url: str | None) -> User:
        user.facebook_id = facebook_id
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
        self.db.commit()
        self.db.refresh(user)
        return user

    def upsert_supabase_user(
        self,
        *,
        user_id: UUID,
        email: str | None,
        name: str,
        avatar_url: str | None = None,
    ) -> User:
        """Sync Supabase auth.users row into local users (same UUID as sub)."""
        user = self.get_by_id(user_id)
        if user:
            if email and not user.email:
                user.email = email.lower()
            if name:
                user.name = name
            if avatar_url:
                user.avatar_url = avatar_url
            self.db.commit()
            self.db.refresh(user)
            return user
        user = User(
            id=user_id,
            email=email.lower() if email else None,
            name=name.strip() or "User",
            avatar_url=avatar_url,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
