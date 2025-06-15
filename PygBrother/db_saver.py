from typing import Callable
from praw.models.mod_action import ModAction
from praw.models.reddit.comment import Comment
from praw.models.reddit.redditor import Redditor
from praw.models.reddit.submission import Submission
from sqlalchemy.orm import Session as SQLAlchemySession
from .models import PostModel, CommentModel, UserModel, ModActionModel
from sqlalchemy.exc import SQLAlchemyError

from .log import get_logger
logger = get_logger()

class DatabaseSaver:
    def __init__(self, session_factory: Callable[[], SQLAlchemySession]) -> None:
        self.session_factory: Callable[[], SQLAlchemySession] = session_factory


    def save_post(self, post: Submission) -> None:
        session: SQLAlchemySession = self.session_factory()
        trans_session: SQLAlchemySession = self.session_factory()
        try:
            ex_post = trans_session.query(PostModel).filter_by(reddit_id=post.id).first()
            if ex_post:
                logger.debug(f"Post {ex_post.reddit_id} already exists in the database.")
                return
            # Save user if not present
            if post.author:
                user = trans_session.query(UserModel).filter_by(reddit_id=post.author.name).first()
                if not user:
                    session.add(UserModel.from_praw(post.author))
            session.add(PostModel.from_praw(post))
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error saving post: {e}")
        finally:
            trans_session.close()
            session.close()

    def save_comment(self, comment: Comment) -> None:
        session: SQLAlchemySession = self.session_factory()
        trans_session: SQLAlchemySession = self.session_factory()
        try:
            ex_comment = trans_session.query(CommentModel).filter_by(reddit_id=comment.id).first()
            if ex_comment:
                logger.debug(f"Comment {ex_comment.reddit_id} already exists in the database.")
                return
            # Save user if not present (lookup by reddit_id)
            if comment.author:
                user = trans_session.query(UserModel).filter_by(reddit_id=comment.author.name).first()
                if not user:
                    session.add(UserModel.from_praw(comment.author))
            # Save post if not present (lookup by reddit_id)
            if comment.submission:
                post = trans_session.query(PostModel).filter_by(reddit_id=comment.submission.id).first()
                poster = comment.submission.author
                if not post:
                    if poster is not None:
                        user = trans_session.query(UserModel).filter_by(reddit_id=poster.name).first()
                        if not user and (poster.name != comment.author.name):
                            session.add(UserModel.from_praw(poster))
                    session.add(PostModel.from_praw(comment.submission))
            session.add(CommentModel.from_praw(comment))
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error saving comment: {e}")
        finally:
            trans_session.close()
            session.close()

    # dic = {
    #       "modaction": modaction,
    #       "target": redditor_target
    # }
    def save_modaction(self, dic: dict[str, ModAction|Redditor]) -> None:
        session: SQLAlchemySession = self.session_factory()
        trans_session: SQLAlchemySession = self.session_factory()
        modaction = dic['modaction']
        target = dic['target']
        try:
            ex_modaction = trans_session.query(ModActionModel).filter_by(reddit_id=modaction.id).first()
            if ex_modaction:
                logger.debug(f"ModAction {ex_modaction.reddit_id} already exists in the database.")
                return
            if modaction.target_author:
                user = trans_session.query(UserModel).filter_by(reddit_id=target.name).first()
                if not user: #and target.name != "[deleted]":
                    session.add(UserModel.from_praw(target))
            if modaction.mod:
                user = trans_session.query(UserModel).filter_by(reddit_id=modaction.mod.name).first()
                if not user:
                    session.add(UserModel.from_praw(modaction.mod))
            session.add(ModActionModel.from_praw(modaction))
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error saving mod action: {e}")
        finally:
            trans_session.close()
            session.close()
