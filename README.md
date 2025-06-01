# PygBrother
A moderation bot for subreddits in Python.

## Usage

To run the Reddit fetcher:

```fish
pip install -r requirements.txt
set -x REDDIT_CLIENT_ID your_id
set -x REDDIT_CLIENT_SECRET your_secret
set -x REDDIT_USER_AGENT 'PygBrotherBot/0.1 by yourusername'
set -x SUBREDDIT python
set -x DATABASE_URL sqlite:///pygbrother.db
python -m PygBrother.main
```

You can subscribe your own functions to process posts or comments by using the `post_publisher.subscribe` or `comment_publisher.subscribe` methods in `main.py`.

---
