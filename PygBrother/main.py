# Example usage for RedditFetcher
# To run: set environment variables for Reddit API and database, then run main.py
#
# set -x REDDIT_CLIENT_ID your_id
# set -x REDDIT_CLIENT_SECRET your_secret
# set -x REDDIT_USER_AGENT 'PygBrotherBot/0.1 by yourusername'
# set -x SUBREDDIT python
# set -x DATABASE_URL sqlite:///pygbrother.db
# python -m PygBrother.main

from time import sleep
from .reddit_fetcher import RedditFetcher
from typing import Optional
from .models import PostModel, CommentModel
from .db_saver import DatabaseSaver
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .log import get_logger
from .models import Base  # <-- Add this import

import os

logger = get_logger()

def print_post(post: PostModel) -> None:
    logger.info(f"New post: {post.title} by {post.author.name if post.author else 'Unknown'}")

def print_comment(comment: CommentModel) -> None:
    print(f"New comment: {comment.body[:40]}... by {comment.author.name if comment.author else 'Unknown'}")

def main() -> None:
    praw_config: dict[str, str] = {
        'client_id': os.environ.get('REDDIT_CLIENT_ID', "empty"),
        'client_secret': os.environ.get('REDDIT_CLIENT_SECRET', "empty"),
        'refresh_token': os.environ.get('REDDIT_REFRESH_TOKEN', "empty"),
        'user_agent': os.environ.get('REDDIT_USER_AGENT', 'PygBrotherBot/0.1'),
    }
    #praw_config: dict[str, str] = {k: v for k, v in praw_config_raw.items() if v and v != "none"}
    db_url: str = os.environ.get('DATABASE_URL', 'postgresql+psycopg2://pygbrother:Soleil123@localhost:15432/pygbrother-dev')
    # logger.info(f"Using database URL: {db_url}")
    # exit()
    engine = create_engine(db_url, pool_size=10, max_overflow=20)

    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    subreddit: str = os.environ.get('SUBREDDIT', 'python')
    fetcher: RedditFetcher = RedditFetcher(subreddit, praw_config)
    db_saver = DatabaseSaver(Session)
    fetcher.post_publisher.subscribe(db_saver.save_post)
    fetcher.comment_publisher.subscribe(db_saver.save_comment)
    fetcher.modaction_publisher.subscribe(db_saver.save_modaction)
    fetcher.run()


if __name__ == '__main__':
    main()
