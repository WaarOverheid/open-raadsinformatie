import datetime
import glob
import json
import re
import translitcodec
from lxml import etree
from string import Formatter

from ocd_backend.exceptions import MissingTemplateTag
from elasticsearch.helpers import scan, bulk


def normalize_motion_id(motion_id, date_as_str=None):
    """
    Normalizes forms of motion ids
    """

    regexes = [
        r'^M(?P<year>\d{4})\s*\-\s*(?P<id>\d+)',
        r'^(?P<year>\d{4})\s*M\s*(?P<id>\d+)',
        r'^(?P<year>\d{4})\s*\-\s*(?P<id>\d+)',
        r'^M\s+(?P<id>\d+)'
    ]

    for regex in regexes:
        res = re.match(regex, motion_id.upper())
        if res is not None:
            try:
                year = res.group('year')
            except IndexError as e:
                year = None
            if year is None:
                if date_as_str is None:
                    date_as_str = datetime.datetime.now().isoformat()
                year = date_as_str[0:4]
            mid = res.group('id')
            return u'%sM%s' % (year, mid,)
    return None


def reindex(client, source_index, target_index, target_client=None, chunk_size=500, scroll='5m', transformation_callable=None):
    """
    Reindex all documents from one index to another, potentially (if
    `target_client` is specified) on a different cluster.

    .. note::

        This helper doesn't transfer mappings, just the data.

    :arg client: instance of :class:`~elasticsearch.Elasticsearch` to use (for
        read if `target_client` is specified as well)
    :arg source_index: index (or list of indices) to read documents from
    :arg target_index: name of the index in the target cluster to populate
    :arg target_client: optional, is specified will be used for writing (thus
        enabling reindex between clusters)
    :arg chunk_size: number of docs in one chunk sent to es (default: 500)
    :arg scroll: Specify how long a consistent view of the index should be
        maintained for scrolled search
    """
    target_client = client if target_client is None else target_client

    docs = scan(client, index=source_index, scroll=scroll, _source_include=['*'])
    def _change_doc_index(hits, index):
        for h in hits:
            h['_index'] = index
            if transformation_callable is not None:
                h = transformation_callable(h)
            yield h

    return bulk(target_client, _change_doc_index(docs, target_index),
        chunk_size=chunk_size, stats_only=True)


class ExtendedFormatter(Formatter):
    """An extended format string formatter
    Formatter with extended conversion symbol
    See: https://stackoverflow.com/a/46160537/5081021
    """
    def convert_field(self, value, conversion):
        """ Extend conversion symbol
        Following additional symbol has been added
        * c: convert to string and capitalize
        * l: convert to string and low case
        * u: convert to string and up case

        default are:
        * s: convert with str()
        * r: convert with repr()
        * a: convert with ascii()
        """

        if conversion == "c":
            return str(value).capitalize()
        elif conversion == "u":
            return str(value).upper()
        elif conversion == "l":
            return str(value).lower()
        # Do the default conversion or raise error if no matching conversion found
        super(ExtendedFormatter, self).convert_field(value, conversion)

        # return for None case
        return value


def load_sources_config(path):
    """Loads a JSON file(s) containing the configuration of the available
    sources.

    :param path: the path of the JSON file(s) wildcards * enabled.
    :type path: str.
    """

    def sort_source_keys(key):
        """Sort importance of specified key"""
        try:
            if key[0] == 'key':
                return int(0)
            if str(key[1]).startswith('{key'):
                return int(1)
            if type(key[1]) == list or type(key[1]) == dict:
                return int(4)
            if '{' in str(key[1]):
                return int(2)
        except AttributeError:
            pass
        return int(3)

    def replace_tags(data, chain=None):
        """Replace tags by higher level defined values in yaml files."""
        if type(data) == dict:
            if not chain or 'key' in data:
                chain = dict()
            chain.update(data)

            new_data = dict()
            for key, value in sorted(data.items(), key=sort_source_keys):
                if key[0:1] == '_':
                    continue

                if isinstance(value, basestring):
                    try:
                        new_data[key] = ExtendedFormatter().format(value, **chain)
                        chain[key] = new_data[key]
                    except KeyError, e:
                        raise MissingTemplateTag('Missing template tag %s in configuration for key \'%s\'' % (e, key))
                else:
                    chain[key] = value
                    new_data[key] = replace_tags(value, chain)
            return new_data
        elif type(data) == list:
            new_data = list()
            for value in data:
                new_data.append(replace_tags(value, chain))
            return new_data
        else:
            return data

    from yaml import load
    try:
        from yaml import CLoader as Loader
    except ImportError:
        from yaml import Loader

    result = {}
    for filename in glob.glob(path):
        try:
            ext = filename[-4:]
            with open(filename) as file:
                if ext == 'yaml':
                    data = load(file, Loader=Loader)
                    data = replace_tags(data)

                    for key, entry in data.items():
                        result[key] = entry
                elif ext == 'json':
                    for entry in json.load(file):
                        result[entry['id']] = entry

        except IOError, e:
            e.strerror = 'Unable to load sources configuration file (%s)' % (
                e.strerror,)
            raise

    return result


def load_object(path):
    """Load an object given it's absolute object path, and return it.

    The object can be a class, function, variable or instance.

    :param path: absolute object path (i.e. 'ocd_backend.extractor.BaseExtractor')
    :type path: str.
    """
    try:
        dot = path.rindex('.')
    except ValueError:
        raise ValueError, "Error loading object '%s': not a full path" % path

    module, name = path[:dot], path[dot+1:]
    try:
        mod = __import__(module, {}, {}, [''])
    except ImportError, e:
        raise ImportError, "Error loading object '%s': %s" % (path, e)

    try:
        obj = getattr(mod, name)
    except AttributeError:
        raise NameError, "Module '%s' doesn't define any object named '%s'" % (
            module, name)

    return obj


def try_convert(conv, value):
    try:
        return conv(value)
    except ValueError:
        return value


def parse_date(regexen, date_str):
    """
        Parse a messy string into a granular date

        `regexen` is of the form [ (regex, (granularity, groups -> datetime)) ]
    """
    if date_str:
        for reg, (gran, dater) in regexen:
            m = re.match(reg, date_str)
            if m:
                try:
                    return gran, dater(m.groups())
                except ValueError:
                    return 0, None
    return 0, None


def parse_date_span(regexen, date1_str, date2_str):
    """
        Parse a start & end date into a (less) granular date

        `regexen` is of the form [ (regex, (granularity, groups -> datetime)) ]
    """
    date1_gran, date1 = parse_date(regexen, date1_str)
    date2_gran, date2 = parse_date(regexen, date2_str)

    if date2:
        # TODO: integrate both granularities
        if (date1_gran, date1) == (date2_gran, date2):
            return date1_gran, date1
        if (date2 - date1).days < 5*365:
            return 4, date1
        if (date2 - date1).days < 50*365:
            return 3, date1
        if (date2 - date1).days >= 50*365:
            return 2, date1
    else:
        return date1_gran, date1


class DatetimeJSONEncoder(json.JSONEncoder):
    """
    JSONEncoder that can handle ``datetime.datetime``, ``datetime.date`` and
    ``datetime.timedelta`` objects.
    """
    def default(self, o):
        if isinstance(o, datetime.datetime) or isinstance(o, datetime.date):
            return o.isoformat()
        elif isinstance(o, datetime.timedelta):
            return (datetime.datetime.min + o).time().isoformat()
        else:
            return super(DatetimeJSONEncoder, self).default(o)

_punct_re = re.compile(r'[\t\r\n !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')


def slugify(text, delim=u'-'):
    """Generates an ASCII-only slug."""
    result = []
    for word in _punct_re.split(text.lower()):
        word = word.encode('translit/long')
        if word:
            result.append(word)
    return unicode(delim.join(result))


def strip_namespaces(item):
    xslt = '''
    <xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:output method="xml" indent="no"/>

    <xsl:template match="/|comment()|processing-instruction()">
        <xsl:copy>
          <xsl:apply-templates/>
        </xsl:copy>
    </xsl:template>

    <xsl:template match="*">
        <xsl:element name="{local-name()}">
          <xsl:apply-templates select="@*|node()"/>
        </xsl:element>
    </xsl:template>

    <xsl:template match="@*">
        <xsl:attribute name="{local-name()}">
          <xsl:value-of select="."/>
        </xsl:attribute>
    </xsl:template>
    </xsl:stylesheet>
    '''

    xslt_root = etree.XML(xslt)
    transform = etree.XSLT(xslt_root)

    return transform(item)


def json_datetime(o):
    if isinstance(o, datetime.datetime):
        return o.__str__()


def get_secret(item_id):
    try:
        from ocd_backend.secrets import SECRETS
    except ImportError:
        raise UserWarning("The SECRETS variable in ocd_backend/secrets.py "
                          "does not exist. Copy secrets.default.py to "
                          "secrets.py and make sure that SECRETS is correct.")

    try:
        return SECRETS[item_id]
    except:
        for k in sorted(SECRETS, key=len, reverse=True):
            if item_id.startswith(k):
                return SECRETS[k]
        raise UserWarning("No secrets found for %s! Make sure that the "
                          "correct secrets are supplied in ocd_backend/"
                          "secrets.py" % item_id)


def propagate_chain_get(terminal_node, timeout=None):
    for node in reversed(list(terminal_node._parents())):
        try:
            node.get(propagate=True, timeout=timeout)
        except:
            pass
