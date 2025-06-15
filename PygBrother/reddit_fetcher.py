from typing import Callable, Dict, Optional, TypeVar, Generic
import praw
from praw import Reddit
from praw.models.mod_action import ModAction
from praw.models.reddit.comment import Comment
from praw.models.reddit.redditor import Redditor
from praw.models.reddit.submission import Submission
from praw.models.reddit.subreddit import Subreddit
import prawcore
from threading import Event
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
    # def __init__(self) -> None:
    #     self.subscribers: list[Callable[[T], None]] = []
    def __init__(self, subreddit: str, praw_config: Dict[str, str]) -> None:
        self.client_id: str = praw_config['client_id']
        self.user_agent: str = praw_config['user_agent']
        self.client_secret: str = praw_config['client_secret']
        self.refresh_token: str = praw_config['refresh_token'] if 'refresh_token' in praw_config else ''
        self.connect()
        self.subreddit: Subreddit = self.reddit.subreddit(subreddit)
        
        try:
            _ = self.reddit.user.me()
        except prawcore.exceptions.OAuthException as e:
           logger.error(f"Failed to authenticate Reddit user: {str(e)}")
           raise e

        logger.info(f"Logged in to Reddit as u/{self.reddit.user.me().name}")

        try:
            if not self.subreddit.user_is_moderator:
                raise PermissionError(f"u/{self.reddit.user.me().name} is not a mod in r/{self.subreddit.display_name}")
        except prawcore.exceptions.Forbidden:
            raise PermissionError(f"r/{subreddit} is private or quarantined.")
        except prawcore.exceptions.NotFound:
            raise ValueError(f"r/{subreddit} is banned.")

        self.stop_event: Event = Event()
        self.post_publisher: Publisher[Submission] = Publisher()
        self.comment_publisher: Publisher[Comment] = Publisher()
        self.modaction_publisher: Publisher[dict[str, ModAction | Redditor]] = Publisher()
        self.subscribers: list[Callable[[T], None]] = []


    def connect(self) -> None:
        """
        Connect to the Reddit API using credentials from environment variables.
        
        Returns:
            None
        """
        try:
            self.reddit: Reddit = Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                refresh_token=self.refresh_token,
                user_agent=self.user_agent
            )
            logger.info("Successfully connected to Reddit API")
        except Exception as e:
            logger.error(f"Failed to initialize Reddit connection: {str(e)}")
            raise
    


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
        redditor_target: Redditor | None = self.reddit.redditor(modaction.target_author) if modaction.target_author else None
        dic = {
            "modaction": modaction,
            "target": redditor_target
        }
        self.modaction_publisher.notify(dic)

    def fetch_post_by_id(self, post_id: str) -> Optional[Submission]:
        """
        Fetch a post by its ID.
        
        Args:
            post_id (str): The ID of the post to fetch.
        
        Returns:
            Optional[Submission]: The fetched post or None if not found.
        """
        try:
            submission: Submission = self.reddit.submission(id=post_id)
            return submission
        except prawcore.exceptions.NotFound:
            logger.warning(f"Post with ID {post_id} not found.")
            return None
    
    def fetch_comment_by_id(self, comment_id: str) -> Optional[Comment]:
        """
        Fetch a comment by its ID.
        
        Args:
            comment_id (str): The ID of the comment to fetch.
        
        Returns:
            Optional[Comment]: The fetched comment or None if not found.
        """
        try:
            return self.reddit.comment(id=comment_id)
        except prawcore.exceptions.NotFound:
            logger.warning(f"Comment with ID {comment_id} not found.")
            return None
        
    def fetch_user_by_name(self, username: str) -> Optional[Redditor]:
        """
        Fetch a user by their username.
        
        Args:
            username (str): The username of the user to fetch.
        
        Returns:
            Optional[Redditor]: The fetched user or None if not found.
        """
        try:
            return self.reddit.redditor(username)
        except prawcore.exceptions.NotFound:
            logger.warning(f"User {username} not found.")
            return None

    def fetch_modactions_by_id(self, modaction_id: str) -> Optional[ModAction]:
        """
        Fetch a mod action by its ID.

        Args:
            modaction_id (str): The ID of the mod action to fetch.

        Returns:
            Optional[ModAction]: The fetched mod action or None if not found.
        """
        try:
            return self.reddit.modaction(id=modaction_id)
        except prawcore.exceptions.NotFound:
            logger.warning(f"Mod action with ID {modaction_id} not found.")
            return None
        
    def fetch_latest_posts(self, limit: int = 10) -> list[Submission]:
        """
        Fetch the latest posts from the subreddit.
        
        Args:
            limit (int): The maximum number of posts to fetch.
        
        Returns:
            list[Submission]: A list of the latest posts.
        """
        return list(self.subreddit.new(limit=limit))
    
    def fetch_latest_comments(self, limit: int = 10) -> list[Comment]:
        """
        Fetch the latest comments from the subreddit.
        
        Args:
            limit (int): The maximum number of comments to fetch.
        
        Returns:
            list[Comment]: A list of the latest comments.
        """
        return list(self.subreddit.comments(limit=limit))
    
    def fetch_latest_modactions(self, limit: int = 10) -> list[ModAction]:
        """
        Fetch the latest mod actions from the subreddit.
        
        Args:
            limit (int): The maximum number of mod actions to fetch.
        
        Returns:
            list[ModAction]: A list of the latest mod actions.
        """
        return list(self.subreddit.mod.log(limit=limit))

