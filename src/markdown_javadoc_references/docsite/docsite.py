import os.path
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Callable

import requests.exceptions
from bs4 import BeautifulSoup

from .util import check_url, read_url, is_file
from ..entities import Klass, Type
from ..util import get_logger

logger = get_logger(__name__)

executor = ThreadPoolExecutor(max_workers=32)

class Docsite:
    def __init__(self, klasses: dict[str, list[Klass]], lazy_load: Callable[[Klass], None]):
        self.klasses = klasses
        self._klasses_for_ref_cached = lru_cache(maxsize=None)(self._klasses_for_ref_uncached)
        self._lazy_load = lazy_load

    def klasses_for_ref(self, class_name: str) -> list[Klass]:
        return self._klasses_for_ref_cached(class_name)

    # lazy load done here
    def _klasses_for_ref_uncached(self, class_name: str) -> list[Klass]:
        if class_name not in self.klasses:
            return list()
        found = self.klasses[class_name]

        found_names = list()
        for c in found:
            found_names.append(f" {c.name} -> {c.url}) ||")
        logger.debug(f"Found classes: {found_names} for reference {class_name}")

        found = self.klasses[class_name]

        def ensure_members(klass: Klass):
            if klass.type is None:
                self._lazy_load(klass)
            if klass.type is None: # if still None, error occurred -> set type to Class to not raise any errors
                klass.type = Type.CLASS
            return klass

        found = list(executor.map(ensure_members, found))

        return found

@lru_cache(maxsize=None)
def load(raw_url: str, type: str | None) -> Docsite | None:
    from .jdk8 import load as jdk8_load
    from .jdk9 import load as jdk9_load

    url = _resolve_special(raw_url)
    if url is None:
        return None

    # check if url is reachable
    try:
        resp = check_url(url + '/index.html')
        if not resp.ok:
            logger.error(f"Couldn't open site {url}, got {resp.status_code} - skipping it... Perhaps misspelled?")
            return None
    except requests.exceptions.RequestException:
        logger.error(f"Couldn't open site {url} - skipping it... Perhaps misspelled?")
        return None

    # /allclasses-noframe.html only exists pre java 9
    f_type = type if type is not None else ('old' if check_url(f'{url}/allclasses-noframe.html').ok else 'new')

    return jdk8_load(url) if f_type == 'old' else jdk9_load(url)

def _resolve_special(url: str) -> str | None:
    if url.startswith('https://javadoc.io/doc'):
        stripped =  url.removesuffix('index.html').removesuffix('/')
        if stripped.endswith('latest'):
            stripped = _resolve_javadocio_latest(stripped)
            if stripped is None:
                return None
        return stripped.replace('/doc/', '/static/', 1)
    if is_file(url):
        return os.path.abspath(url)

    return url

def _resolve_javadocio_latest(stripped: str) -> str | None:
    text = read_url(stripped)
    if text is None:
        return None
    soup = BeautifulSoup(text, "html.parser")
    version_nav  = soup.findAll(attrs={'class': 'nav-link dropdown-toggle'})
    if len(version_nav) != 2:
        logger.error("Unknown javadoc.io version of latest link!")
        return None
    version = version_nav[1].text.strip()
    return stripped.replace('/latest', f'/{version}')
