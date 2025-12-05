import urllib.parse

from bs4 import BeautifulSoup
from bs4.element import Tag

from .docsite import Docsite
from .util import read_url, find_class_type
from ..entities import Klass, Method, Field
from ..util import get_logger

logger = get_logger(__name__)

def load(url: str) -> Docsite | None:
    # info is intended
    logger.info(f'Loading java 8 docs.. may take a while: {url}')

    text = read_url(f'{url}/allclasses-noframe.html')
    if text is None:
        return None

    soup = BeautifulSoup(text, 'html.parser')

    klasses = dict()

    for anchor in soup.find('body').find('div').find('ul').select('a[href]'):
        klass = _load_class(url, anchor)

        # append subclasses as individual classes
        for name in klass.name.split('.'):
            klasses.setdefault(name, []).append(klass)

    return Jdk8(klasses)


# noinspection PyTypeChecker
def _load_class(url: str, c: Tag) -> Klass:
    logger.debug(f"Loading jdk8 class: {url}")
    name = c.get_text(strip=True)
    package = c.get('title').split()[-1]

    klass = Klass(None, package, name, None, None, None, f'{url}/{c.get("href")}')
    logger.debug(f'Loaded {package}.{name} from {klass.url}')

    return klass


def _load_members(klass: Klass):
    logger.debug(f"Loading members for: {klass}")

    text = read_url(klass.url)

    klass.methods = list()
    klass.fields = list()

    if text is None:
        return

    soup = BeautifulSoup(text, "html.parser")
    anchors = {a.get("name") for a in soup.find_all("a", attrs={"name": True})}
    for a in anchors:
        parts = a.split('-')
        unquoted_url = urllib.parse.unquote(f'{klass.url}#{a}')
        # first part is always name
        member_name = parts[0]

        # is field
        if len(parts) <= 1:
            klass.fields.append(Field(member_name, unquoted_url, klass))

        if member_name == klass.name:
            member_name = '<init>' # normalize constructor method names to <init>
        new_params = []

        # following parts are parameters
        for param in parts[1:]:

            # skip empty strings - they're not real parameters
            if len(param) == 0:
                continue

            # split at : - after it there are metadata like A for arrays
            name_split = param.split(':')
            new_name = name_split[0]

            # add [] for arrays
            if len(name_split) == 2:
                new_name = new_name + ('[]' * (name_split[1].count('A')))

            new_params.append(new_name.strip())


        klass.methods.append(Method(klass, member_name, new_params, unquoted_url))

    logger.debug(f"Found {len(klass.methods)} classes and {len(klass.fields)} fields for {klass.name} ({klass.url})")

    # find class type
    title = soup.find("h2", attrs={"class": "title"})
    klass.type = find_class_type(title.text, klass)

class Jdk8(Docsite):
    def __init__(self, klasses):
        super().__init__(klasses, _load_members)



