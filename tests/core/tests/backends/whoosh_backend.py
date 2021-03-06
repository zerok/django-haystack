import datetime
import os
from whoosh.qparser import QueryParser
from django.conf import settings
from django.test import TestCase
from haystack import indexes
from haystack.backends.whoosh_backend import SearchBackend
from haystack import sites
from core.models import MockModel, AnotherMockModel


class WhooshMockSearchIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr='author')
    pub_date = indexes.DateField(model_attr='pub_date')


class WhooshSearchSite(sites.SearchSite):
    pass


class WhooshSearchBackendTestCase(TestCase):
    def setUp(self):
        super(WhooshSearchBackendTestCase, self).setUp()
        
        # Stow.
        temp_path = os.path.join('tmp', 'test_whoosh_query')
        self.old_whoosh_path = getattr(settings, 'HAYSTACK_WHOOSH_PATH', temp_path)
        settings.HAYSTACK_WHOOSH_PATH = temp_path
        
        self.site = WhooshSearchSite()
        self.sb = SearchBackend(site=self.site)
        self.smmi = WhooshMockSearchIndex(MockModel, backend=self.sb)
        self.site.register(MockModel, WhooshMockSearchIndex)
        
        self.sb.setup()
        self.raw_whoosh = self.sb.index
        self.parser = QueryParser(self.sb.content_field_name, schema=self.sb.schema)
        self.raw_whoosh.delete_by_query(q=self.parser.parse('*'))
        
        self.sample_objs = []
        
        for i in xrange(1, 4):
            mock = MockModel()
            mock.id = i
            mock.author = 'daniel%s' % i
            mock.pub_date = datetime.date(2009, 2, 25) - datetime.timedelta(days=i)
            self.sample_objs.append(mock)
    
    def tearDown(self):
        if os.path.exists(settings.HAYSTACK_WHOOSH_PATH):
            index_files = os.listdir(settings.HAYSTACK_WHOOSH_PATH)
        
            for index_file in index_files:
                os.remove(os.path.join(settings.HAYSTACK_WHOOSH_PATH, index_file))
        
            os.removedirs(settings.HAYSTACK_WHOOSH_PATH)
        
        settings.HAYSTACK_WHOOSH_PATH = self.old_whoosh_path
        super(WhooshSearchBackendTestCase, self).tearDown()
    
    def whoosh_search(self, query):
        searcher = self.raw_whoosh.searcher()
        return searcher.search(self.parser.parse(query))
    
    def test_update(self):
        self.sb.update(self.smmi, self.sample_objs)
        
        # Check what Whoosh thinks is there.
        self.assertEqual(len(self.whoosh_search('*')), 3)
        self.assertEqual([dict(doc) for doc in self.whoosh_search('*')], [{'django_id_s': u'3', 'django_ct_s': u'core.mockmodel', 'name': u'daniel3', 'text': u'Indexed!\n3', 'pub_date': u'2009-02-22', 'id': u'core.mockmodel.3'}, {'django_id_s': u'2', 'django_ct_s': u'core.mockmodel', 'name': u'daniel2', 'text': u'Indexed!\n2', 'pub_date': u'2009-02-23', 'id': u'core.mockmodel.2'}, {'django_id_s': u'1', 'django_ct_s': u'core.mockmodel', 'name': u'daniel1', 'text': u'Indexed!\n1', 'pub_date': u'2009-02-24', 'id': u'core.mockmodel.1'}])
    
    def test_remove(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(len(self.whoosh_search('*')), 3)
        
        self.sb.remove(self.sample_objs[0])
        self.assertEqual(len(self.whoosh_search('*')), 2)
        self.assertEqual([dict(doc) for doc in self.whoosh_search('*')], [{'django_id_s': u'3', 'django_ct_s': u'core.mockmodel', 'name': u'daniel3', 'text': u'Indexed!\n3', 'pub_date': u'2009-02-22', 'id': u'core.mockmodel.3'}, {'django_id_s': u'2', 'django_ct_s': u'core.mockmodel', 'name': u'daniel2', 'text': u'Indexed!\n2', 'pub_date': u'2009-02-23', 'id': u'core.mockmodel.2'}])
    
    def test_clear(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(len(self.whoosh_search('*')), 3)
        
        self.sb.clear()
        self.raw_whoosh = self.sb.index
        self.assertEqual(self.raw_whoosh.doc_count(), 0)
        
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(len(self.whoosh_search('*')), 3)
        
        self.sb.clear([AnotherMockModel])
        self.assertEqual(len(self.whoosh_search('*')), 3)
        
        self.sb.clear([MockModel])
        self.raw_whoosh = self.sb.index
        self.assertEqual(self.raw_whoosh.doc_count(), 0)
        
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(len(self.whoosh_search('*')), 3)
        
        self.sb.clear([AnotherMockModel, MockModel])
        self.raw_whoosh = self.sb.index
        self.assertEqual(self.raw_whoosh.doc_count(), 0)
    
    def test_search(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(len(self.whoosh_search('*')), 3)
        
        self.assertEqual(self.sb.search(''), [])
        self.assertEqual(self.sb.search('*')['hits'], 3)
        self.assertEqual([result.pk for result in self.sb.search('*')['results']], [u'3', u'2', u'1'])
        
        self.assertEqual(self.sb.search('', highlight=True), [])
        self.assertEqual(self.sb.search('Index*', highlight=True)['hits'], 3)
        # DRL_FIXME: Uncomment once highlighting works.
        # self.assertEqual([result.highlighted['text'][0] for result in self.sb.search('Index*', highlight=True)['results']], ['<em>Indexed</em>!\n3', '<em>Indexed</em>!\n2', '<em>Indexed</em>!\n1'])
        
        self.assertEqual(self.sb.search('', facets=['name']), [])
        results = self.sb.search('Index*', facets=['name'])
        self.assertEqual(results['hits'], 3)
        self.assertEqual(results['facets'], {})
        
        self.assertEqual(self.sb.search('', date_facets={'pub_date': {'start_date': datetime.date(2008, 2, 26), 'end_date': datetime.date(2008, 2, 26), 'gap': '/MONTH'}}), [])
        results = self.sb.search('Index*', date_facets={'pub_date': {'start_date': datetime.date(2008, 2, 26), 'end_date': datetime.date(2008, 2, 26), 'gap': '/MONTH'}})
        self.assertEqual(results['hits'], 3)
        self.assertEqual(results['facets'], {})
        
        self.assertEqual(self.sb.search('', query_facets={'name': '[* TO e]'}), [])
        results = self.sb.search('Index*', query_facets={'name': '[* TO e]'})
        self.assertEqual(results['hits'], 3)
        self.assertEqual(results['facets'], {})
        
        # self.assertEqual(self.sb.search('', narrow_queries=['name:daniel1']), [])
        # results = self.sb.search('Index*', narrow_queries=['name:daniel1'])
        # self.assertEqual(results['hits'], 1)
    
    def test_more_like_this(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assertEqual(len(self.whoosh_search('*')), 3)
        
        # Unsupported by Whoosh. Should see empty results.        
        self.assertEqual(self.sb.more_like_this(self.sample_objs[0])['hits'], 0)
    
    def test_delete_index(self):
        self.sb.update(self.smmi, self.sample_objs)
        self.assert_(self.sb.index.doc_count() > 0)
        
        self.sb.delete_index()
        self.assertEqual(self.sb.index.doc_count(), 0)
