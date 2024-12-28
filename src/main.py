import os
import random
import string
import time
import logging
from typing import Union, Tuple
from praw import Reddit
from praw.models import Submission, Comment
from dotenv import load_dotenv
import pickledb
from typing import Callable
import threading

log_format = "%(asctime)s: %(threadName)s: %(message)s"
logging.basicConfig(format=log_format, level=logging.INFO, datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
CLIENT = os.getenv("CLIENT_ID")
SECRET = os.getenv("CLIENT_SECRET")
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

# Quotes to be posted
QUOTES = [
    "We are the creators of our own reality, the architects of our own destiny.",
    "The soul, like the mind, is never truly free until it has reconciled itself with the uncertainties of existence.",
    "In every moment, we must choose between despair and hope, for it is only through choice that we find meaning.",
    "The true path to wisdom is not through reason alone, but through the balance of emotion and intellect.",
    "Life does not follow the rules of logic; it unfolds in mysterious and unpredictable ways, challenging us to adapt.",
    "To be human is to be constantly in conflict with the world, yet also to find beauty within that struggle.",
    "It is not enough to seek answers; we must embrace the questions that lead us to deeper understanding.",
    "Freedom is not given to us, it is something we must claim for ourselves.",
    "We are all part of a greater story, one that transcends our individual lives and connects us to something far more profound.",
    "True power lies in the ability to shape the world around us, but even more so in the capacity to shape our own thoughts."
]

KEYWORDS = {"reality", "soul", "wisdom", "life", "human", "freedom", "power"}
DONT_COMMENT_KEYWORD = "!nopost"

# Set the path for the database
pickle_path = os.path.dirname(os.path.abspath(__file__)) + "/comments.db"
db = pickledb.load(pickle_path, True)

# Create Reddit object instance using Praw
reddit = Reddit(
    user_agent="pradon-bot",
    client_id=CLIENT,
    client_secret=SECRET,
    username=USERNAME,
    password=PASSWORD,
)

# Helper function to restart threads on failure
def restart(handler: Callable):
    def wrapped_handler(*args, **kwargs):
        logger.info("Starting thread with: %s", args)
        while True:
            try:
                handler(*args, **kwargs)
            except Exception as e:
                logger.error("Exception: %s", e)

    return wrapped_handler

@restart
def iterate_comments(subreddit_name: str):
    """
    Iterate through subreddit comments and respond with a random quote if keywords are found
    """
    sub = reddit.subreddit(subreddit_name)

    for comment in sub.stream.comments():
        logger.debug(f"Analyzing comment: {comment.body}")
        should_comment = should_comment_on_comment(comment)
        if should_comment:
            write_comment(comment)
            logger.info(f"Added comment to comment: {str(comment.body)}")
        else:
            logger.debug("Not commenting")

@restart
def iterate_posts(subreddit_name: str):
    """
    Iterate through subreddit posts and respond with a random quote if keywords are found
    """
    sub = reddit.subreddit(subreddit_name)

    for post in sub.stream.submissions():
        logger.debug(f"Analyzing post: {post.title}")
        should_comment = should_comment_on_post(post)
        if should_comment:
            write_comment(post)
            logger.info(f"Added comment to post: {str(post.title)}")
        else:
            logger.debug("Not commenting")

def should_comment_on_comment(comment: Comment) -> bool:
    """
    Check if a comment should trigger a response based on keywords
    """
    if DONT_COMMENT_KEYWORD.lower() in comment.body.lower():
        return False

    body = standardize_text(comment.body)
    for keyword in KEYWORDS:
        if keyword in body:
            return True
    return False

def should_comment_on_post(post: Submission) -> bool:
    """
    Check if a post should trigger a response based on keywords
    """
    if DONT_COMMENT_KEYWORD.lower() in post.selftext.lower() or DONT_COMMENT_KEYWORD.lower() in post.title.lower():
        return False

    body = standardize_text(post.selftext)
    title = standardize_text(post.title)
    for keyword in KEYWORDS:
        if keyword in body or keyword in title:
            return True
    return False

def write_comment(obj: Union[Comment, Submission]):
    """
    Write a random quote as a comment
    """
    quote = random.choice(QUOTES)
    comment_string = f"{quote}\n\n[^(source)](https://www.reddit.com/user/{USERNAME})"
    obj.reply(comment_string)

def standardize_text(text: str) -> str:
    """
    Standardize the text by removing punctuation and converting to lowercase
    """
    return text.lower().translate(str.maketrans("", "", string.punctuation))

@restart
def listen_and_process_mentions():
    """
    Listen for mentions of the bot and respond with a random quote
    """
    for message in reddit.inbox.stream():
        subject = standardize_text(message.subject)
        if subject == "username mention" and isinstance(message, Comment):
            write_comment(message)
            logger.info(f"Added comment to message: {str(message.body)}")
            message.mark_read()

if __name__ == "__main__":
    logger.info("Main: Creating threads")
    threads = []
    posts_thread = threading.Thread(target=iterate_posts, args=("quotes",), name="posts")
    comments_thread = threading.Thread(target=iterate_comments, args=("quotes",), name="comments")
    mentions_thread = threading.Thread(target=listen_and_process_mentions, name="mentions")

    threads.append(posts_thread)
    threads.append(comments_thread)
    threads.append(mentions_thread)

    logger.info("Main: Starting threads")
    for thread in threads:
        thread.start()
