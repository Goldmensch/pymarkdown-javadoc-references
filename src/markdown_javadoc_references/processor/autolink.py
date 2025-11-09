import re
from collections.abc import Callable
from typing import cast
import xml.etree.ElementTree as etree

from ..reference import raw_pattern as ref_pattern
from markdown.inlinepatterns import InlineProcessor

from ..entities import Klass, Field, Method, Entity, Type
from ..resolver import Resolver
from ..util import get_logger

logger = get_logger(__name__)

def _default_formatter(ref: Entity) -> str:
    match ref:
        case Klass():
            return f"@{ref.name}" if ref.type == Type.ANN_INTERFACE else ref.name
        case Field():
            return f'{ref.klass.name}#{ref.name}'
        case Method():
            return f'{ref.klass.name}#{ref.name}({ref.parameter_names_joined()})'
        case _:
            raise ValueError("Should not occur")

def _compile_formatter(code: str) -> Callable[[Entity], str | etree.Element]:
    namespace = {
        "Klass": Klass,
        "Method": Method,
        "Field": Field,
        "Entity": Entity,
        "Type": Type,
        "etree": etree
    }

    indented = '\n'.join("  " + line for line in code.splitlines())

    wrapper = f"def autolink_format(ref: Entity) -> str | etree.Element:  \n{indented}\n"

    exec(wrapper, namespace)
    return cast(Callable[[Entity], str | etree.Element], namespace["autolink_format"])

auto_link_pattern: str = rf'<(?!init>)({ref_pattern})>'

class AutoLinkJavaDocProcessor(InlineProcessor):
    def __init__(self, md, resolver: Resolver, autolink_format: str):
        super().__init__(auto_link_pattern, md)
        self.resolver = resolver
        self.formatter = _compile_formatter(autolink_format) if autolink_format != '' else _default_formatter

    def handleMatch(self, m: re.Match, data: str):
        logger.debug(f"Handle auto link match: {m.group(0)}")

        ref, el = self.resolver.resolve(m.group('whole_ref'), m.group(1))
        if ref is not None:
            try:
                formatted = self.formatter(ref)

                match formatted:
                    case str():
                        el.text = formatted
                    case etree.Element():
                        el.text = None
                        el.append(formatted)

            except Exception as e:
                logger.error(f"Error while evaluating autolink ({el.get('href')}): {e}")
                el.text = el.get('href')

        return el, m.start(0), m.end(0)
