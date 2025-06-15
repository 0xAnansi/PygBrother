
from PygBrother.log import get_logger
from PygBrother.reddit_fetcher import RedditFetcher
from praw.models.mod_action import ModAction
from praw.models.reddit.comment import Comment
from praw.models.reddit.redditor import Redditor
from praw.models.reddit.submission import Submission

import os
import pytest

logger = get_logger()

@pytest.fixture(scope="module")
def fetcher():
    praw_config: dict[str, str] = {
        'client_id': os.environ.get('REDDIT_CLIENT_ID', "empty"),
        'client_secret': os.environ.get('REDDIT_CLIENT_SECRET', "empty"),
        'refresh_token': os.environ.get('REDDIT_REFRESH_TOKEN', "empty"),
        'user_agent': os.environ.get('REDDIT_USER_AGENT', 'PygBrotherBot/0.1'),
    }
    subreddit: str = os.environ.get('SUBREDDIT', 'python')
    logger.info(f"Using subreddit: {subreddit} with UA: {praw_config['user_agent']}")
    return RedditFetcher(subreddit, praw_config)

def test_fetch_real_submission(fetcher: RedditFetcher):
    post_list = fetcher.fetch_latest_posts(limit=1)
    assert post_list is not None
    post = post_list.pop()
    assert isinstance(post, Submission)
    assert hasattr(post, "title")
    print(f"Fetched submission: {post.title}")

def test_fetch_real_comment(fetcher: RedditFetcher):
    comment_list = fetcher.fetch_latest_comments(limit=1)
    assert comment_list is not None
    comment = comment_list.pop()
    assert isinstance(comment, Comment)
    assert hasattr(comment, "body")
    print(f"Fetched comment: {comment.body[:40]}")

def test_fetch_real_user(fetcher: RedditFetcher):
    post_list = fetcher.fetch_latest_posts(limit=1)
    assert post_list is not None
    post = post_list.pop()
    user = post.author
    assert user is not None
    assert hasattr(user, "name")
    print(f"Fetched user: {user.name}")

def test_fetch_real_modaction(fetcher: RedditFetcher):
    modaction_list = fetcher.fetch_latest_modactions(limit=1)
    assert modaction_list is not None
    modaction = modaction_list.pop()
    assert isinstance(modaction, ModAction)
    assert hasattr(modaction, "action")
    print(f"Fetched modaction by mod: {getattr(modaction, 'mod', 'unknown')}, type: {getattr(modaction, 'action_type', 'unknown')}")
