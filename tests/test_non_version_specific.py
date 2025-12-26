import os.path

import markdown
from markdown_javadoc_references import JavaDocRefExtension

default_urls = [
    'https://docs.oracle.com/en/java/javase/24/docs/api/',
]

def compare(expected, text, urls=default_urls, autolink_format=''):
    result = markdown.markdown(text, extensions=[JavaDocRefExtension(urls=urls, **{'autolink-format': autolink_format})])

    assert result == expected

### non version specific tests
def test_normal_autolink_still_work():
    expected = '<p><a href="https://www.google.com">https://www.google.com</a></p>'
    compare(expected, "<https://www.google.com>")

def test_autolink_only_class():
    expected = '<p><a href="https://docs.oracle.com/en/java/javase/24/docs/api/java.base/java/lang/String.html">String</a></p>'
    compare(expected, "<String>")

def test_autolink_only_class_with_package():
    expected = '<p><a href="https://docs.oracle.com/en/java/javase/24/docs/api/java.base/java/lang/String.html">String</a></p>'
    compare(expected, "<java.lang.String>")

def test_autolink_annotation():
    expected = '<p><a href="https://docs.oracle.com/en/java/javase/24/docs/api/java.base/java/lang/annotation/Retention.html">@Retention</a></p>'
    compare(expected, "<java.lang.annotation.Retention>")

def test_autolink_only_class_with_package_custom_formatter_str():
    autolink_format = """   
    match ref:
        case Klass():
            return f'{ref.package}.{ref.name}'
    """

    expected = '<p><a href="https://docs.oracle.com/en/java/javase/24/docs/api/java.base/java/lang/String.html">java.lang.String</a></p>'
    compare(expected, "<java.lang.String>", autolink_format=autolink_format)

def test_autolink_only_class_with_package_custom_formatter_etree():
    autolink_format = """   
    match ref:
        case Klass():
            code = etree.Element('code')
            code.text = f'{ref.package}.{ref.name}'
            return code
    """

    expected = '<p><a href="https://docs.oracle.com/en/java/javase/24/docs/api/java.base/java/lang/String.html"><code>java.lang.String</code></a></p>'
    compare(expected, "<java.lang.String>", autolink_format=autolink_format)

def test_autolink_with_parameters():
    expected = '<p><a href="https://docs.oracle.com/en/java/javase/24/docs/api/java.base/java/lang/String.html#join(java.lang.CharSequence,java.lang.CharSequence...)">String#join(CharSequence, CharSequence...)</a></p>'
    compare(expected, "<String#join(CharSequence, CharSequence...)>")

def test_autolink_in_codeblock():
    expected = '<p><code>&lt;String#join(CharSequence, CharSequence...)&gt;</code></p>'
    compare(expected, "`<String#join(CharSequence, CharSequence...)>`")

def test_javadoc_alias_whole_url():
    urls = [
        'https://docs.oracle.com/en/java/javase/24/docs/api/',
        'https://docs.oracle.com/javase/8/docs/api/'
    ]

    expected = '<p><a href="https://docs.oracle.com/javase/8/docs/api/java/lang/String.html">String</a></p>'
    compare(expected, "<https://docs.oracle.com/javase/8/docs/api/ -> String>", urls=urls)

def test_javadoc_alias_custom_alias():
    urls = [
        'https://docs.oracle.com/en/java/javase/24/docs/api/',
        {
            'alias': 'jdk8',
            'url': 'https://docs.oracle.com/javase/8/docs/api/'
        }
    ]

    expected = '<p><a href="https://docs.oracle.com/javase/8/docs/api/java/lang/String.html">String</a></p>'
    compare(expected, "<jdk8 -> String>", urls=urls)

def test_javadoc_alias_custom_alias_two_in_one_line():
    urls = [
        {
            'alias': 'jdk8',
            'url': 'https://docs.oracle.com/javase/8/docs/api/'
        }
    ]

    expected = '<p><a href="https://docs.oracle.com/javase/8/docs/api/java/lang/String.html">String</a> Hu hu my test <a href="https://docs.oracle.com/javase/8/docs/api/java/lang/String.html">String</a></p>'
    compare(expected, "<String> Hu hu my test <jdk8 -> String>", urls=urls)

def test_javadoc_not_auto_searched_not_found():
    urls = [
        {
            'alias': 'jdk8',
            'url': 'https://docs.oracle.com/javase/8/docs/api/',
            'auto_searched': 'false'
        }
    ]

    expected = '<p><a href="String">Invalid reference to String</a></p>'
    compare(expected, "<String>", urls=urls)

def test_javadoc_not_auto_searched_found():
    urls = [
        {
            'alias': 'jdk8',
            'url': 'https://docs.oracle.com/javase/8/docs/api/',
            'auto_searched': 'false'
        }
    ]

    expected = '<p><a href="https://docs.oracle.com/javase/8/docs/api/java/lang/String.html">String</a></p>'
    compare(expected, "<jdk8 -> String>", urls=urls)


def test_site_not_found_alias():
    urls = [
        'https://notworkingdocs.com',
    ]

    expected = '<p><a href="jdk8 -&gt; String">Invalid reference to jdk8 -&gt; String</a></p>'
    compare(expected, "<jdk8 -> String>", urls=urls)

def test_site_not_found():
    urls = [
        'https://notworkingdocs.com',
    ]

    expected = '<p><a href="String">Invalid reference to String</a></p>'
    compare(expected, "<String>", urls=urls)

def test_multiple_in_text_link_with_codeblocks():
    text = """
You can use [`Strings`][[String]]
or something else like [`StringBuilders`][[StringBuilder]]"""

    expected = """<p>You can use <a href="https://docs.oracle.com/en/java/javase/24/docs/api/java.base/java/lang/String.html"><code>Strings</code></a>
or something else like <a href="https://docs.oracle.com/en/java/javase/24/docs/api/java.base/java/lang/StringBuilder.html"><code>StringBuilders</code></a></p>"""

    compare(expected, text)

def test_multiple_in_text_link():
    text = """
You can use [Strings][[String]]
or something else like [StringBuilders][[StringBuilder]]"""

    expected = """<p>You can use <a href="https://docs.oracle.com/en/java/javase/24/docs/api/java.base/java/lang/String.html">Strings</a>
or something else like <a href="https://docs.oracle.com/en/java/javase/24/docs/api/java.base/java/lang/StringBuilder.html">StringBuilders</a></p>"""

    compare(expected, text)

def test_multiple_in_text_autolink():
    text = """
You can use <String>
or something else like <StringBuilder>
"""

    expected = """<p>You can use <a href="https://docs.oracle.com/en/java/javase/24/docs/api/java.base/java/lang/String.html">String</a>
or something else like <a href="https://docs.oracle.com/en/java/javase/24/docs/api/java.base/java/lang/StringBuilder.html">StringBuilder</a></p>"""

    compare(expected, text)

def test_type_new_specific():
    urls = [
        {
            'type': 'new',
            'url': 'https://docs.oracle.com/en/java/javase/24/docs/api/'
        }
    ]

    expected = '<p><a href="https://docs.oracle.com/en/java/javase/24/docs/api/java.base/java/lang/String.html">String</a></p>'
    compare(expected, "<String>", urls=urls)

def test_type_old_specific():
    urls = [
        {
            'type': 'old',
            'url': 'https://docs.oracle.com/javase/8/docs/api/'
        }
    ]

    expected = '<p><a href="https://docs.oracle.com/javase/8/docs/api/java/lang/String.html">String</a></p>'
    compare(expected, "<String>", urls=urls)

def test_file_origin():
    base_path = os.path.abspath(".")
    if not base_path.endswith('tests'):
        base_path  += '/tests'

    urls = [
        base_path + '/local_docs/jdk9/docs/javadoc'
    ]

    expected = f'<p><a href="file://{base_path}/local_docs/jdk9/docs/javadoc/io.github.kaktushose.jdac.core/io/github/kaktushose/jdac/JDACBuilder.html">JDACBuilder</a></p>'
    compare(expected, "<JDACBuilder>", urls=urls)