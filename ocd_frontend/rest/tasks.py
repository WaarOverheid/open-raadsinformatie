import json
from datetime import datetime

from ocd_frontend import settings
from ocd_frontend.es import ElasticsearchService
from ocd_frontend.factory import create_celery_app
from ocd_frontend.helpers import root_path

celery = create_celery_app()

es_service = ElasticsearchService(
    settings.ELASTICSEARCH_HOST,
    settings.ELASTICSEARCH_PORT
)

# PUT Elasticsearch mapping
log_mapping_file = 'ori_mapping_usage_logs.json'
with open(root_path('es_mappings', log_mapping_file)) as f:
    log_mapping = json.load(f)

logging_index = settings.USAGE_LOGGING_INDEX
print('Putting {} as mapping for {}'.format(log_mapping_file, logging_index))
es_service.put_mapping(
    index=logging_index,
    body=log_mapping
)


@celery.task(ignore_result=True)
def log_event(user_agent, referer, user_ip, created_at, event_type, **kwargs):
    """Log user activity events to the specified 'usage logging'
    ElasticSearch index.

    :param user_agent: the user's raw user agent string
    :type user_agent: str
    :param referer: the contents of the HTTP referer request header
    :type referer: str or None
    :param user_ip: the user's pseudonymized IP address
    :type user_ip: str
    :param created_at: the datetime when the event was created (in UTC)
    :type created_at: datetime.datetime
    :event_type: the name of the event type; available event types are
                 specified under ``available_event_types``
    :param kwargs: any additional arguments will be passed on to the
                   function responsible for processing the event
    """

    available_event_types = {
        'search': search_event,
        'search_similar': search_similar_event,
        'sources': sources_event,
        'get_object': get_object_event,
        'get_object_source': get_object_event,
        'resolve': resolve_event,
        'resolve_thumbnail': resolve_thumbnail
    }

    if event_type not in available_event_types:
        raise ValueError('"%s" is an unknown event type' % event_type)

    # Base structure of an event
    event = {
        'created_at': created_at,
        'processed_at': datetime.utcnow(),
        'user_properties': {
            'user_agent': user_agent,
            'referer': referer,
            'ip': user_ip
        },
        'event_properties': available_event_types[event_type](**kwargs)
    }

    es_service.create(index=settings.USAGE_LOGGING_INDEX,
                      doc_type=event_type, body=event)

    return event


def search_event(query, hits, n_total_hits, query_time_ms, source_id=None, doc_type=None):
    """Format the properties of the ``search`` event.

    :param query: a dictionary that specifies the query and it's options
    :type query: dict
    :param hits: a list of the returned hits. Each item in the list should
                 contain a dictionary with the document and source ID.
    :type hits: list
    :param n_total_hits: number of total hists that matched the query
    :type n_total_hits: int
    :param query_time_ms: duration of the query in milliseconds
    :type query_time_ms: int
    :param source_id: specifies which index was targeted. If ``source_id``
                      is ``None``, the search was executed against the
                      combined index.
    :type source_id: str or None
    :param doc_type: specifies the document type (if any)
    :type doc_type: str or None
    """

    return {
        'source_id': source_id,
        'doc_type': doc_type,
        'query': query,
        'hits': hits,
        'n_total_hits': n_total_hits,
        'query_time_ms': query_time_ms
    }


def search_similar_event(similar_to_source_id, similar_to_object_id, query,
                         hits, n_total_hits, query_time_ms):
    """Format the properties of the ``search_similar`` event.

    :param similar_to_source_id: specifies which index was targeted. If
                                 ``similar_to_source_id`` is ``None``, the
                                 similarity search was executed against the
                                 combined index.
    :type similar_to_source_id: str or None
    :param similar_to_object_id: the ID of the object for which similar
                                 items are requested.
    :type similar_to_object_id: str
    :param query: a dictionary that specifies the query and it's options
    :type query: dict
    :param hits: a list of the returned hits. Each item in the list should
                 contain a dictionary with the document and source ID.
    :type hits: list
    :param n_total_hits: number of total hists that matched the query
    :type n_total_hits: int
    :param query_time_ms: duration of the query in milliseconds
    :type query_time_ms: int
    """
    return {
        'similar_to_object': {
            'source_id': similar_to_source_id,
            'object_id': similar_to_object_id
        },
        'query': query,
        'hits': hits,
        'n_total_hits': n_total_hits,
        'query_time_ms': query_time_ms
    }


def sources_event(query_time_ms):
    """Format the properties of the ``sources`` event.

    :param query_time_ms: duration of the query in milliseconds
    :type query_time_ms: int
    """
    return {
        'query_time_ms': query_time_ms
    }


def get_object_event(source_id, object_id):
    """Format the properties of the ``get_object`` event.

    :param source_id: the ID of the source to which the document belongs
    :type source_id: str
    :param object_id: the ID of the requested object
    :type object_id: str
    """
    return {
        'source_id': source_id,
        'object_id': object_id
    }


def resolve_event(url_id):
    """Format the properties of the ``resolve`` event.

    :param url_id: the resolve ID of the URL that was resolved
    :type url_id: str
    """
    return {
        'url_id': url_id
    }


def resolve_thumbnail(url_id, requested_size='original'):
    """Format the properties of the ``resolve_thumbnail`` event.

    :param url_id: the resolve ID of the URL that was resolved
    :type url_id: str
    :param requested_size: Thumbnails can be requested in different sizes, log
                           which one was requested
    """
    return {
        'url_id': url_id,
        'requested_size': requested_size
    }
