from django.db import models
from django.test import TestCase
from haystack.indexes import BasicSearchIndex
from haystack.sites import SearchSite, AlreadyRegistered, NotRegistered
from core.models import MockModel, AnotherMockModel


class MockNotAModel(object):
    pass


class SearchSiteTestCase(TestCase):
    def setUp(self):
        super(SearchSiteTestCase, self).setUp()
        self.site = SearchSite()
    
    def test_register(self):
        self.assertRaises(AttributeError, self.site.register, MockNotAModel)
        
        self.site.register(MockModel)
        self.assertEqual(len(self.site._registry), 1)
        self.assert_(MockModel in self.site._registry)
        
        self.assertRaises(AlreadyRegistered, self.site.register, MockModel)
    
    def test_unregister(self):
        self.assertRaises(NotRegistered, self.site.unregister, MockModel)
        
        # Depends on proper function of register.
        self.site.register(MockModel)
        self.site.unregister(MockModel)
        self.assertEqual(len(self.site._registry), 0)
        self.assertFalse(MockModel in self.site._registry)
    
    def test_get_index(self):
        self.assertRaises(NotRegistered, self.site.get_index, MockModel)
        
        self.site.register(MockModel)
        self.assert_(isinstance(self.site.get_index(MockModel), BasicSearchIndex))
    
    def test_get_indexes(self):
        self.assertEqual(self.site.get_indexes(), {})
        
        self.site.register(MockModel)
        indexes = self.site.get_indexes()
        self.assert_(isinstance(indexes, dict))
        self.assertEqual(len(indexes), 1)
        self.assert_(MockModel in indexes)
    
    def test_get_indexed_models(self):
        self.assertEqual(self.site.get_indexed_models(), [])
        
        self.site.register(MockModel)
        indexed_models = self.site.get_indexed_models()
        self.assertEqual(len(indexed_models), 1)
        self.assert_(MockModel in indexed_models)
    
    def test_build_unified_schema(self):
        self.site.register(MockModel)
        content_field_name, fields = self.site.build_unified_schema()
        self.assertEqual(content_field_name, 'text')
        self.assertEqual(fields, [{'indexed': 'true', 'type': 'text', 'field_name': 'text', 'multi_valued': 'false'}])
        
        self.site.register(AnotherMockModel)
        content_field_name, fields = self.site.build_unified_schema()
        self.assertEqual(content_field_name, 'text')
        self.assertEqual(fields, [{'indexed': 'true', 'type': 'text', 'field_name': 'text', 'multi_valued': 'false'}])
