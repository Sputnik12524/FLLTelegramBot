from datetime import datetime
from typing import Optional, List

from sqlalchemy import BigInteger, String, ForeignKey, Integer, JSON, Boolean, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs
"""
engine = create_async_engine('sqlite+aiosqlite:///mydatabase.db', echo=True)
async_session = async_sessionmaker(engine)
"""


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base, AsyncAttrs):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    team_id: Mapped[Optional[int]] = mapped_column(ForeignKey('teams.id'), nullable=True)

    team: Mapped['UserTeams'] = relationship(back_populates='users')

    def __repr__(self):
        return f"<User(id={self.id}, tg_id={self.tg_id}, team_id={self.team_id})>"


class UserTeams(Base, AsyncAttrs):
    __tablename__ = 'teams'

    id: Mapped[int] = mapped_column(primary_key=True)
    team: Mapped[str] = mapped_column(String(100), unique=True)
    city: Mapped[str] = mapped_column(String(100))
    number: Mapped[int] = mapped_column(Integer, unique=True,
                                        index=True)  # <<< number должен быть UNIQUE и INDEXED для ForeignKey
    password: Mapped[str] = mapped_column(String(30), unique=True)

    users: Mapped[List['User']] = relationship(back_populates='team')

    def __repr__(self):
        return f"<UserTeams(id={self.id}, team='{self.team}', number={self.number})>"


class Patent(Base, AsyncAttrs):
    __tablename__ = 'patents'

    id: Mapped[int] = mapped_column(primary_key=True)

    team_number: Mapped[int] = mapped_column(ForeignKey('teams.number'))

    caption: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(String(250))

    missions: Mapped[List[int]] = mapped_column(JSON)
    image_ids: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    video_ids: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    approved: Mapped[bool] = mapped_column(Boolean, default=False)  # <<< Новое поле с дефолтом False
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Patent(id={self.id}, team_number={self.team_number}, caption='{self.caption}')>"


class Record(Base):
    __tablename__ = 'records'
    id: Mapped[int] = mapped_column(primary_key=True)
    r_team: Mapped[int] = mapped_column(ForeignKey('teams.id'))
    result: Mapped[int] = mapped_column(Integer)
    video_id: Mapped[int] = mapped_column(BigInteger)


class FLLResult(Base, AsyncAttrs):
    __tablename__ = 'fll_results'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_tg_id: Mapped[int] = mapped_column(BigInteger, index=True)
    team_id: Mapped[Optional[int]] = mapped_column(ForeignKey('teams.id'), nullable=True)
    
    # Сохраняем результаты миссий как JSON
    mission_scores: Mapped[dict] = mapped_column(JSON)
    total_score: Mapped[int] = mapped_column(Integer)
    max_possible_score: Mapped[int] = mapped_column(Integer)
    
    # Метаданные
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Название результата
    
    def __repr__(self):
        return f"<FLLResult(id={self.id}, user_tg_id={self.user_tg_id}, total_score={self.total_score})>"
