import json
import os
from mock import MagicMock
from pprint import pprint

from lxml import etree
import iso8601

from ocd_backend.items.go_report import ReportItem

from . import ItemTestCase


class ReportItemTestCase(ItemTestCase):
    def setUp(self):
        super(ReportItemTestCase, self).setUp()
        self.PWD = os.path.dirname(__file__)
        dump_path = os.path.abspath(os.path.join(self.PWD, '../test_dumps/den_helder_archived_meeting.html'))
        self.pdf_path = os.path.abspath(os.path.join(self.PWD, '../test_dumps/Besluitenlijst-raadsvergadering-29-juni-2015.pdf'))

        self.source_definition = {
            "id": "den_helder_resolutions",
            "extractor": "ocd_backend.extractors.go.GemeenteOplossingenResolutionsExtractor",
            "transformer": "ocd_backend.transformers.BaseTransformer",
            "item": "ocd_backend.items.go_meeting.ReportItem",
            "enrichers": [],
            "loader": "ocd_backend.loaders.ElasticsearchLoader",
            "cleanup": "ocd_backend.tasks.CleanupElasticsearch",
            "hidden": False,
            "index_name": "den_helder",
            "doc_type": "events",
            "keep_index_on_update": True,
            "base_url": "https://gemeenteraad.denhelder.nl",
            "extract_meeting_items": False,
            "upcoming": False
        }

        with open(dump_path, 'r') as f:
            self.raw_item = f.read()

        self.meeting = {
            'type': 'meeting',
            'content': self.raw_item,
            'full_content': self.raw_item
        }

        self.meeting_object_id = u'https://gemeenteraad.denhelder.nl/Vergaderingen/Gemeenteraad/2015/29-juni/17:00/#downloaden'
        self.meeting_object_urls = {
            'html': u'https://gemeenteraad.denhelder.nl/Vergaderingen/Gemeenteraad/2015/29-juni/17:00/#downloaden',
            'mp3': u'https://gemeenteraad.denhelder.nl/Vergaderingen/Gemeenteraad/2015/29-juni/17:00/download/880/mp3'
        }

        self.rights = u'undefined' # for now ...
        self.collection = u'Verslag Gemeenteraad 29 juni 2015 17:00:00'

        self.meeting_name = u'Verslag Gemeenteraad 29 juni 2015 17:00:00'

        self.meeting_identifiers = [
            {
                'identifier': u'https://gemeenteraad.denhelder.nl/Vergaderingen/Gemeenteraad/2015/29-juni/17:00/#downloaden',
                'scheme': u'GemeenteOplossingen'
            },
            {
                'identifier': '0a905ec9d547f863fbb0acfdde81b868e8a8098f',
                'scheme': u'ORI'
            }
        ]

        self.meeting_classification = u'Report'

        self.start_date = iso8601.parse_date(u'2015-06-29T17:00:00')
        self.location = u'Gemeentehuis'
        self.status = u'confirmed'


        self.meeting_sources = [
            {
                'url': u'https://gemeenteraad.denhelder.nl/Vergaderingen/Gemeenteraad/2015/29-juni/Besluitenlijst-raadsvergadering-29-juni-2015.pdf',
                'note': u'Besluitenlijst raadsvergadering 29 juni 2015.pdf'
            },
            {
                'url': u'https://gemeenteraad.denhelder.nl/Vergaderingen/Gemeenteraad/2015/29-juni/Oproep-vergadering-gemeenteraad-6.pdf',
                'note': u'Oproep vergadering gemeenteraad.pdf'
            },
            {
                'url': u'https://gemeenteraad.denhelder.nl/Vergaderingen/Gemeenteraad/2015/29-juni/17:00/download/880/mp3',
                'note': u'1. 2015-06-29-16-53-36-Gemeenteraad.mp3'
            }
        ]

        self.organisation = {'id': u'1', 'name': u'Den Helder'}

        self.meeting_description = u''

    def _instantiate_meeting(self):
        """
        Instantiate the item from the raw and parsed item we have
        """

        # # FIXME: these need to return some values
        ReportItem._get_council = MagicMock(return_value={'id': u'1', 'name': u'Den Helder'})
        ReportItem._get_committees = MagicMock(return_value={})
        item = ReportItem(
            self.source_definition, 'application/json',
            self.raw_item, self.meeting
        )

        return item


    def test_meeting_get_original_object_id(self):
        item = self._instantiate_meeting()
        self.assertEqual(item.get_original_object_id(), self.meeting_object_id)

    def test_meeting_get_original_object_urls(self):
        item = self._instantiate_meeting()
        self.assertDictEqual(
            item.get_original_object_urls(), self.meeting_object_urls)

    def test_meeting_get_rights(self):
        item = self._instantiate_meeting()
        self.assertEqual(item.get_rights(), self.rights)


    def test_meeting_get_collection(self):
        item = self._instantiate_meeting()
        self.assertEqual(item.get_collection(), self.collection)


    def test_meeting_name(self):
        item = self._instantiate_meeting()
        data = item.get_combined_index_data()
        self.assertEqual(data['name'], self.meeting_name)


    def test_meeting_identifiers(self):
        item = self._instantiate_meeting()
        data = item.get_combined_index_data()
        self.assertEqual(data['identifiers'], self.meeting_identifiers)


    def test_meeting_organisation(self):
        item = self._instantiate_meeting()
        data = item.get_combined_index_data()
        self.assertDictEqual(data['organisation'], self.organisation)


    def test_meeting_classification(self):
        item = self._instantiate_meeting()
        data = item.get_combined_index_data()
        self.assertEqual(data['classification'], self.meeting_classification)


    def test_meeting_dates(self):
        item = self._instantiate_meeting()
        data = item.get_combined_index_data()
        self.assertEqual(data['start_date'], self.start_date)
        self.assertEqual(data['end_date'], self.start_date)


    def test_meeting_location(self):
        item = self._instantiate_meeting()
        data = item.get_combined_index_data()
        self.assertEqual(data['location'], self.location)


    def test_meeting_status(self):
        item = self._instantiate_meeting()
        data = item.get_combined_index_data()
        self.assertEqual(data['status'], self.status)


    def test_meeting_sources(self):
        item = self._instantiate_meeting()
        data = item.get_combined_index_data()
        self.assertEqual(data['sources'], self.meeting_sources)


    def test_meeting_description(self):
        item = self._instantiate_meeting()
        data = item.get_combined_index_data()
        self.assertEqual(data['description'], u'')
