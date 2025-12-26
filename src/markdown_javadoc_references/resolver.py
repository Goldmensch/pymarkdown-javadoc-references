from concurrent.futures import ThreadPoolExecutor

from .docsite import docsite
from .docsite.docsite import Docsite
from .reference import create_or_none
from .reference import Type
from .entities import Entity

import xml.etree.ElementTree as etree

from .util import get_logger

logger = get_logger(__name__)

def _matches(klasses, reference):
    links = dict()

    # search in each class
    for klass in klasses:
        joined_klass = klass.package + '.' + klass.name

        # if package is given -> compare package + class. Subclasses in references are treated as package
        if reference.package is not None:
            joined_reference = reference.package + '.' + reference.class_name
            if not joined_klass.endswith(joined_reference):
                continue
        elif not joined_klass.endswith(reference.class_name):
            continue

        # compare method if given
        if reference.member_name is not None:
            if reference.type == Type.METHOD:
                # get all methods for class
                methods = klass.methods
                # search in each member
                for method in methods:
                    # compare method name
                    if reference.member_name != method.name:
                        continue
                    # compare parameter size
                    if len(reference.parameters) != len(method.parameters):
                        continue

                    # compare parameters
                    parameter_match = True
                    for r_p, m_p in zip(reference.parameters, method.parameters):
                        if not m_p.endswith(r_p):
                            parameter_match = False
                    if not parameter_match:
                        continue

                    links[method.url] = method
            else:
                # get all fields
                fields = klass.fields

                # compare each field
                for field in fields:
                    if reference.member_name == field.name:
                        links[field.url] = field

        else:  # if not given, just reference found class
            links[klass.url] = klass

    return links


def _process_url(url: str, type: str | None):
    logger.debug(f"Process url {url}")

    stripped_url = url.removesuffix('/')
    return docsite.load(stripped_url, type)

executor = ThreadPoolExecutor(max_workers=8)

class LoadedSite:
    def __init__(self, site: Docsite, auto_searched: bool):
        self.auto_searched = auto_searched
        self.site = site

def _create_site(site: Docsite | None, auto_searched: bool):
    if site is None:
        return None
    return LoadedSite(site, auto_searched)

class Resolver:
    def __init__(self, urls):
        self.sites = dict()

        def process(entry):
            if isinstance(entry, str):
                processed = _process_url(entry, None)
                return entry.strip(), _create_site(processed, True)
            elif isinstance(entry, dict)  and 'url' in entry:
                type = entry['type'] if 'type' in entry else None
                processed = _process_url(entry['url'], type)

                auto_searched = 'auto_searched' not in entry or entry['auto_searched'] == 'true'
                alias = entry['alias'] if 'alias' in entry else entry['url']
                return alias.strip(), _create_site(processed, auto_searched)
            else:
                raise TypeError(
                    f"Invalid entry in urls config: {entry!r}. "
                    f"Expected string or dict with 'alias' and 'url'."
                )

        for alias, site in executor.map(process, urls):
            if site is not None:
                self.sites[alias] = site

    def resolve(self, text: str, ref: str) -> tuple[Entity | None, etree.Element]:
        logger.debug(f"Resolving link with text {text} and reference {ref}")

        el = etree.Element('a')
        el.text = text
        el.set('href', ref)

        reference = create_or_none(ref)
        if reference is not None:
            links = self._find_matching_javadoc(reference)

            if len(links) == 0:
                logger.warning(f'No javadoc matching {ref} was found!')
                el.text = f'Invalid reference to {ref}'
            elif len(links) > 1:
                logger.warning(
                    f'Multiple javadoc matching {ref} found! Please be more specific, maybe add a pacakge? Found javadocs: {'; '.join(links)}')
                el.text = f'Invalid reference to {ref}'
            else:
                link, ref = next(iter(links.items()))

                if not link.startswith('http'):
                    link = f"file://{link}"

                el.set('href', link)
                return ref, el
        else:
            logger.debug(f"Invalid reference for {text} and {ref}")

        return None, el

    def _find_matching_javadoc(self, reference) -> dict[str, Entity]:
        def load(site):
            klasses = site.klasses_for_ref(reference.class_name)
            if klasses is None:
                return dict()
            return _matches(klasses, reference)

        if reference.javadoc_alias is not None:
            if reference.javadoc_alias not in self.sites:
                logger.warning(f"URL alias {reference.javadoc_alias} is not defined in the config!")
                return dict()
            return load(self.sites[reference.javadoc_alias].site)

        def process_site(item):
            alias, meta = item
            if not meta.auto_searched:
                return None
            return load(meta.site)


        futures = list(executor.map(process_site, self.sites.items()))

        links = {}
        for result in futures:
            if result:
                links |= result

        return links
