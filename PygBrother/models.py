from __future__ import annotations
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone
from typing import Optional, Type, TypeVar, ClassVar
from praw.models.mod_action import ModAction
from praw.models.reddit.comment import Comment
from praw.models.reddit.redditor import Redditor
from praw.models.reddit.submission import Submission
import prawcore
from .log import get_logger

logger = get_logger()

Base = declarative_base()

T = TypeVar('T', bound='UserModel')

class UserModel(Base):
    __tablename__: ClassVar[str] = 'users'
    id = Column(Integer, primary_key=True)
    reddit_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    created_utc = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    link_karma = Column(Integer, default=0)
    comment_karma = Column(Integer, default=0)
    is_mod = Column(Integer, default=0)
    icon_img = Column(String)
    modactions = relationship('ModActionModel', back_populates='target_author')
    posts = relationship('PostModel', back_populates='author')
    comments = relationship('CommentModel', back_populates='author')

    @classmethod
    def from_praw(cls: Type[T], praw_user: Redditor) -> Optional[T]:
        if praw_user.name == '[deleted]':
            return cls(
                reddit_id=praw_user.name,
                name=praw_user.name,
                link_karma=0,
                comment_karma=0,
                is_mod=0,
                icon_img=None
        )
        # Do some dodgy error checking since praw dan return 404 some times
        _reddit_id=praw_user.name
        _name=praw_user.name
        try:
            _link_karma=getattr(praw_user, 'link_karma', 0)
        except prawcore.exceptions.NotFound:
            logger.warning(f"User {praw_user.name} not found, setting link_karma to -1")
            _link_karma=-1
        try:
            _comment_karma=getattr(praw_user, 'comment_karma', 0)
        except prawcore.exceptions.NotFound:
            logger.warning(f"User {praw_user.name} not found, setting comment_karma to -1")
            _comment_karma=-1
        _is_mod=int(getattr(praw_user, 'is_mod', False))
        _icon_img=getattr(praw_user, 'icon_img', None)

        return cls(
            reddit_id=_reddit_id,
            name=_name,
            link_karma=_link_karma,
            comment_karma=_comment_karma,
            is_mod=_is_mod,
            icon_img=_icon_img
        )

P = TypeVar('P', bound='PostModel')

class PostModel(Base):
    __tablename__: ClassVar[str] = 'posts'
    id = Column(Integer, primary_key=True)
    reddit_id = Column(String, unique=True, nullable=False)
    title = Column(String)
    body = Column(Text)
    created_utc = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    author_id = Column(String, ForeignKey('users.reddit_id'))
    author = relationship('UserModel', back_populates='posts')
    url = Column(String)
    score = Column(Integer, default=0)
    num_comments = Column(Integer, default=0)
    comments = relationship('CommentModel', back_populates='post')
    subreddit = Column(String)
    @classmethod
    def from_praw(cls: Type[P], praw_submission: Submission) -> P:
        return cls(
            reddit_id=praw_submission.id,
            title=praw_submission.title,
            body=praw_submission.selftext,
            created_utc=datetime.fromtimestamp(praw_submission.created_utc, tz=timezone.utc),
            url=praw_submission.url,
            score=praw_submission.score,
            num_comments=praw_submission.num_comments,
            subreddit=str(praw_submission.subreddit),
            author_id=praw_submission.author.name if praw_submission.author else None,
        )


C = TypeVar('C', bound='CommentModel')

class CommentModel(Base):
    __tablename__: ClassVar[str] = 'comments'
    id = Column(Integer, primary_key=True)
    reddit_id = Column(String, unique=True, nullable=False)
    body = Column(Text)
    created_utc = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    author_id = Column(String, ForeignKey('users.reddit_id'))
    author = relationship('UserModel', back_populates='comments')
    post_id = Column(String, ForeignKey('posts.reddit_id'))
    post = relationship('PostModel', back_populates='comments')
    score = Column(Integer, default=0)
    parent_id = Column(String)
    subreddit = Column(String)

    @classmethod
    def from_praw(cls: Type[C], praw_comment: Comment) -> C:
        return cls(
            reddit_id=praw_comment.id,
            body = praw_comment.body,
            created_utc = datetime.fromtimestamp(praw_comment.created_utc, tz=timezone.utc),
            score = praw_comment.score,
            parent_id = praw_comment.parent_id,
            subreddit = str(praw_comment.subreddit),
            author_id = praw_comment.author.name if praw_comment.author else None,
            post_id = getattr(getattr(praw_comment, "submission", None), "id", None),
        )

M = TypeVar('M', bound='ModActionModel')

class ModActionModel(Base):
    __tablename__: ClassVar[str] = 'modactions'
    id = Column(Integer, primary_key=True)
    reddit_id = Column(String, unique=True, nullable=False)
    action = Column(String)
    mod = Column(String)
    mod_id = Column(String)
    target_author_id = Column(String, ForeignKey('users.reddit_id'))
    target_author = relationship('UserModel', back_populates='modactions')
    target_fullname = Column(String)
    description = Column(Text)
    details = Column(Text)
    created_utc = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    subreddit = Column(String)

    @classmethod
    def from_praw(cls: Type[M], praw_modaction: ModAction) -> M:
        return cls(
            reddit_id = praw_modaction.id,
            action = praw_modaction.action,
            mod = praw_modaction.mod.name if praw_modaction.mod else None,
            mod_id = praw_modaction.mod.id if praw_modaction.mod else None,
            target_author_id = praw_modaction.target_author if praw_modaction.target_author else None,
            target_fullname = getattr(praw_modaction, 'target_fullname', None),
            description = getattr(praw_modaction, 'description', None),
            details = getattr(praw_modaction, 'details', None),
            created_utc = datetime.fromtimestamp(praw_modaction.created_utc, tz=timezone.utc),
            subreddit = str(praw_modaction.subreddit)
        )
