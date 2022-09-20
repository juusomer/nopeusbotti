import functools
import os
from dataclasses import dataclass
from typing import Optional

import tweepy


@dataclass(frozen=True)
class Credentials:
    access_token: str
    access_token_secret: str
    api_key: str
    api_key_secret: str

    @staticmethod
    def from_environment():
        return Credentials(
            os.environ["ACCESS_TOKEN"],
            os.environ["ACCESS_TOKEN_SECRET"],
            os.environ["API_KEY"],
            os.environ["API_KEY_SECRET"],
        )


def get_client(credentials: Optional[Credentials] = None):
    return tweepy.Client(
        consumer_key=credentials.api_key,
        consumer_secret=credentials.api_key_secret,
        access_token=credentials.access_token,
        access_token_secret=credentials.access_token_secret,
    )


def send_tweet(
    text: str,
    media_filename: Optional[str] = None,
    credentials: Optional[Credentials] = None,
):
    if credentials is None:
        credentials = Credentials.from_environment()

    if media_filename is not None:
        media_ids = [upload_media(media_filename, credentials).media_id]
    else:
        media_ids = None

    client = get_client(credentials)
    client.create_tweet(text=text, media_ids=media_ids)


def get_username(credentials: Optional[Credentials] = None):
    if credentials is None:
        credentials = Credentials.from_environment()

    return get_client(credentials).get_me().data.username


def upload_media(media_filename: str, credentials: Optional[Credentials] = None):
    auth = tweepy.OAuthHandler(credentials.api_key, credentials.api_key_secret)
    auth.set_access_token(credentials.access_token, credentials.access_token_secret)
    api = tweepy.API(auth)
    return api.media_upload(media_filename)
