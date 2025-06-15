import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from PygBrother.models import Base, UserModel, PostModel, CommentModel
from PygBrother.db_saver import DatabaseSaver
from unittest.mock import MagicMock
import time
from testcontainers.postgres import PostgresContainer

# Use testcontainers to spin up a PostgreSQL container for testing
def pytest_configure():
    os.environ.setdefault('POSTGRES_DB', 'testdb')
    os.environ.setdefault('POSTGRES_USER', 'testuser')
    os.environ.setdefault('POSTGRES_PASSWORD', 'testpass')
    os.environ.setdefault('POSTGRES_PORT', '5433')
    os.environ.setdefault('POSTGRES_HOST', 'localhost')

@pytest.fixture(scope='session')
def pg_engine():
    # Use testcontainers to spin up a PostgreSQL container for testing
    with PostgresContainer('postgres:17.5') as postgres:
        db_url = postgres.get_connection_url().replace('postgresql://', 'postgresql+psycopg2://')
        engine = create_engine(db_url)
        # Wait for DB to be ready
        for _ in range(10):
            try:
                conn = engine.connect()
                conn.close()
                break
            except Exception:
                time.sleep(1)
        Base.metadata.create_all(engine)
        yield engine
        Base.metadata.drop_all(engine)
        engine.dispose()

from sqlalchemy.engine import Engine

@pytest.fixture
def db_session(pg_engine: Engine):
    Session = sessionmaker(bind=pg_engine)
    session = Session()
    yield session
    session.close()

from sqlalchemy.orm import Session

@pytest.fixture
def db_saver(db_session: Session):
    return DatabaseSaver(lambda: db_session)

@pytest.fixture
def mock_redditor():
    user = MagicMock()
    user.name = 'mockuser'
    user.link_karma = 123
    user.comment_karma = 456
    user.is_mod = False
    user.icon_img = 'http://img.url'
    return user

@pytest.fixture
def mock_submission(mock_redditor: MagicMock):
    post = MagicMock()
    post.id = 'abc123'
    post.title = 'Test Post'
    post.selftext = 'Body of post'
    post.created_utc = time.time()
    post.url = 'http://reddit.com/post'
    post.score = 10
    post.num_comments = 2
    post.subreddit = 'testsub'
    post.author = mock_redditor
    return post

@pytest.fixture
def mock_comment(mock_redditor: MagicMock, mock_submission: MagicMock):
    comment = MagicMock()
    comment.id = 'cmt123'
    comment.body = 'Test comment body'
    comment.created_utc = time.time()
    comment.score = 5
    comment.parent_id = 't3_abc1231'
    comment.subreddit = 'testsub'
    comment.author = mock_redditor
    comment.submission = mock_submission
    return comment


def test_save_post(db_saver: DatabaseSaver, db_session: Session, mock_submission: MagicMock):
    db_saver.save_post(mock_submission)
    post = db_session.query(PostModel).filter_by(reddit_id=mock_submission.id).first()
    assert post is not None
    assert post.title == mock_submission.title
    user = db_session.query(UserModel).filter_by(reddit_id=mock_submission.author.name).first()
    assert user is not None
    #time.sleep(99999)


from sqlalchemy.orm import Session

def test_save_comment(db_saver: DatabaseSaver, db_session: Session, mock_comment: MagicMock):
    db_saver.save_comment(mock_comment)
    comment = db_session.query(CommentModel).filter_by(reddit_id=mock_comment.id).first()
    assert comment is not None
    assert comment.body == mock_comment.body
    user = db_session.query(UserModel).filter_by(reddit_id=mock_comment.author.name).first()
    assert user is not None
    post = db_session.query(PostModel).filter_by(reddit_id=mock_comment.submission.id).first()
    assert post is not None

def test_multi_save_comment(db_saver: DatabaseSaver, db_session: Session, mock_comment: MagicMock):
    db_saver.save_comment(mock_comment)
    db_saver.save_comment(mock_comment)
    comment = db_session.query(CommentModel).filter_by(reddit_id=mock_comment.id).first()
    assert comment is not None
    assert comment.body == mock_comment.body
    user = db_session.query(UserModel).filter_by(reddit_id=mock_comment.author.name).first()
    assert user is not None
    post = db_session.query(PostModel).filter_by(reddit_id=mock_comment.submission.id).first()
    assert post is not None
