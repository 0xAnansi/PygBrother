from typing import Any, Callable, Dict, Optional, TypeVar, Generic
import praw
from praw.models.mod_action import ModAction
from praw.reddit import Comment, Redditor, Submission
import prawcore
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession
from .models import Base, UserModel, PostModel, CommentModel, ModActionModel
from threading import Thread, Event
from datetime import datetime, timezone
from .log import get_logger

logger = get_logger()

T = TypeVar('T')

class Publisher(Generic[T]):
    def __init__(self) -> None:
        self.subscribers: list[Callable[[T], None]] = []
    def subscribe(self, callback: Callable[[T], None]) -> None:
        self.subscribers.append(callback)
    def notify(self, item: T) -> None:
        for callback in self.subscribers:
            callback(item)

class RedditFetcher:
    def connect(self) -> praw.Reddit:
        """
        Connect to the Reddit API using credentials from environment variables.
        
        Returns:
            praw.Reddit instance
        """
        try:
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                refresh_token=self.refresh_token,
                user_agent=self.user_agent,
                #username=self.username,
                #password=self.password
            )
            logger.info("Successfully connected to Reddit API")
            return self.reddit
        except Exception as e:
            logger.error(f"Failed to initialize Reddit connection: {str(e)}")
            raise
    def __init__(self, subreddit: str, praw_config: Dict[str, str]) -> None:
        self.client_id: str = praw_config['client_id']
        self.client_secret: str = praw_config['client_secret']
        self.refresh_token: str = praw_config['refresh_token'] if 'refresh_token' in praw_config else ''
        self.user_agent: str = praw_config['user_agent']
        self.connect()
        
       
        _ = self.reddit.user.me()
        logger.info(f"Logged in to Reddit as u/{self.reddit.user.me().name}")
       
        self.subreddit = self.reddit.subreddit(subreddit)

        try:
            if not self.subreddit.user_is_moderator:
                raise Exception(f"u/{self.reddit.user.me().name} is not a mod in r/{self.subreddit.display_name}")
        except prawcore.exceptions.Forbidden:
            raise Exception(f"r/{subreddit} is private or quarantined.")
        except prawcore.exceptions.NotFound:
            raise Exception(f"r/{subreddit} is banned.")

        self.stop_event: Event = Event()
        self.post_publisher: Publisher[Post] = Publisher()
        self.comment_publisher: Publisher[Comment] = Publisher()
        self.modaction_publisher: Publisher[ModAction] = Publisher()
    def run(self) -> None:
        sub_stream = self.subreddit.stream.submissions(skip_existing=True,pause_after=-1)
        com_stream = self.subreddit.stream.comments(skip_existing=True,pause_after=-1)
        mod_stream = self.subreddit.mod.stream.log(skip_existing=True,pause_after=-1)
        logger.info(f"Starting to fetch content from r/{self.subreddit.display_name} using account {self.reddit.user.me()}")
    
        while 1:
            logger.debug(f"Starting new loop to fetch content from r/{self.subreddit.display_name} using account {self.reddit.user.me()}")
            for submission in sub_stream:
                if submission is None:
                    break
                self._process_post(submission)
            #logger.info(f"Starting to fetch comments from r/{self.subreddit.display_name} using account {self.reddit.user.me()}")
            for comment in com_stream:
                if comment is None:
                    break
                self._process_comment(comment)
            #logger.info(f"Starting to fetch mod actions from r/{self.subreddit.display_name} using account {self.reddit.user.me()}")
            for modaction in mod_stream:
                if modaction is None:
                    break
                self._process_modaction(modaction)
    # def stop(self) -> None:
    #     self.stop_event.set()
        
    def _process_post(self, submission: Submission) -> None:
        logger.debug(f"Processing post: {submission.title} by {submission.author.name if submission.author else 'Unknown'}")
        #post: PostModel = PostModel.from_praw(submission)

        self.post_publisher.notify(submission)

    def _process_comment(self, comment: Comment) -> None:
        logger.debug(f"Processing comment: {comment.body[:40]}... by {comment.author.name if comment.author else 'Unknown'}")
        #comment_obj: CommentModel = CommentModel.from_praw(comment)
        
        self.comment_publisher.notify(comment)

    def _process_modaction(self, modaction: ModAction) -> None:
        logger.debug(f"Processing mod action: {modaction.action} by {modaction.mod.name if modaction.mod else 'Unknown'} on {modaction.target_fullname}")

        #modaction_obj: ModActionModel = ModActionModel.from_praw(modaction)  # type: ignore
        redditor_target: Redditor = self.reddit.redditor(modaction.target_author) if modaction.target_author else None
        dic = {
            "modaction": modaction,
            "target": redditor_target
        }
        self.modaction_publisher.notify(dic)

