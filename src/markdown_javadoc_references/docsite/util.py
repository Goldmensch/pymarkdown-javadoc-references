from urllib.error import HTTPError

import requests

from markdown_javadoc_references.entities import Klass, Type
from markdown_javadoc_references.util import get_logger

from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

logger = get_logger(__name__)

def make_session() -> requests.Session:
    session = requests.Session()

    # aggressive retry policy
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
        raise_on_redirect=True,
        raise_on_status=False,
    )

    adapter = HTTPAdapter(
        pool_connections=10,
        pool_maxsize=10,
        max_retries=retry,
        pool_block=True,
    )

    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session

session = make_session()

def read_url(url: str) -> str | None:
    resp = session.get(url)

    try:
        resp.raise_for_status()
    except HTTPError as err:
        logger.warning(f"Couldn't open url {url}, got status code: {err.code} and message {err.reason}")
        return None

    return resp.text


def check_url(url: str) -> requests.Response:
    resp = session.head(url)
    return resp

def find_class_type(text: str, klass: Klass) -> Type | None:
    match text:
        case s if "Enum" in s:
            return Type.ENUM
        case s if "Annotation" in s:
            return Type.ANN_INTERFACE
        case s if "Interface" in s:
            return Type.INTERFACE
        case s if "Record" in s:
            return Type.RECORD
        case s if "Class" in s:
            return Type.CLASS
        case _:
            logger.error(f"Unknown class type in title {text} of {klass.url}")
            return None