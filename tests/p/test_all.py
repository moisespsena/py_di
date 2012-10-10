'''
Created on Sep 26, 2012

@author: Moises P. Sena <moisespsena@gmail.com>
'''
import unittest
from unittest import TestCase
import di
from threading import Thread
from time import sleep

@di.comp()
class SimpleComponent(object): pass

class C1(object):
    def __init__(self,**kwargs):
        self.kwargs = kwargs

class TestScopeRegistry(TestCase):
    def setUp(self):
        self.registry = di.ScopeRegistry()
    
    def test_set_scope(self):
        self.registry[di.Singleton] = di.SingletonComponentInstancesManager()
        
    def test_has_scope(self):
        self.registry[di.Singleton] = di.SingletonComponentInstancesManager()
        assert di.Singleton in self.registry
        
    def test_get_scope(self):
        self.registry[di.Singleton] = di.SingletonComponentInstancesManager()
        assert self.registry[di.Singleton] is not None

class TestSimpleInstanceCreator(TestCase):
    def setUp(self):
        self.creator = di.SimpleInstanceCreator()
        self.container = di.Container()
        
    def test_create_instance_without_params(self):
        obj = self.creator.create_instance(self.container, C1)
        assert isinstance(obj, C1)
        
    def test_create_instance_with_params(self):
        params = {'arg1' : 1000}
        obj = self.creator.create_instance(self.container, C1, **params)
        assert 'arg1' in obj.kwargs
        assert obj.kwargs['arg1'] == 1000

class db_key: pass

@di.comp(scope=di.Singleton)
class Db(object):
    def __init__(self):
        self.x = 1
    dialect = 'pgsql'
    
@di.comp(deps=dict(db=db_key))
class Dao(object):
    def __init__(self, db=None):
        self.db = db
        
@di.comp(factory=True, deps=dict(db=db_key))
class DaoFactory(di.Factory):
    def __init__(self, db=None):
        self.db = db
        
    def get_instance(self):
        return Dao(self.db)

@di.comp(deps=dict(model='Dao'))
class Controller(object):
    def __init__(self, model=None):
        self.model = model

    @di.inject(db=db_key)
    def injected_method(self, arg, db=None):
        return arg, db
    
    def normal_method(self, arg):
        return "# %s" % arg

class custom_comp_dec(di.comp): pass

@custom_comp_dec(deps=dict(c1='Controller'))
class Controller2(object):
    def __init__(self, c1=None):
        self.dialect = None
        self.c1 = c1
    
    @di.inject(model='Dao')
    def post_init(self, model=None):
        self.dialect = model.db.dialect

class Tests(TestCase):
    def test_simple(self):
        container = di.Container()
        container.components['Dao'] = Dao
        container.components[db_key] = Db
    
        db = container.instance_for(db_key)
        c = container.instance_for(Controller)
        
        assert c.model is not None
        assert isinstance(c.model, Dao)
        assert ("a", db) == c.injected_method("a")
        assert c.normal_method("a") == "# a"
        
        c2 = container.instance_for(Controller)
        assert c2.model is not None
        assert ("b", db) == c2.injected_method("b")
        assert c2.normal_method("b") == "# b"
        
    def test_with_instance_factory(self):
        container = di.Container()
        container.components['Dao'] = DaoFactory
        container.components[db_key] = Db
    
        db = container.instance_for(db_key)
        c = container.instance_for(Controller)
        
        assert c.model is not None
        assert isinstance(c.model, Dao)
        assert ("a", db) == c.injected_method("a")
        assert c.normal_method("a") == "# a"
        
        c2 = container.instance_for(Controller)
        assert c2.model is not None
        assert ("b", db) == c2.injected_method("b")
        assert c2.normal_method("b") == "# b"
        
    def test_post_init_callback(self):
        container = di.Container()
        container.components['Dao'] = DaoFactory
        container.components['Controller'] = Controller
        container.components[db_key] = Db
    
        db = container.instance_for(db_key)
        c = container.instance_for(Controller2)
        
        assert c.dialect == db.dialect

##########################################################
# Singleton Per Thread Component Instances Manager Tests #
##########################################################


class SingletonPerThreadComponentManagerTest(TestCase):
    def setUp(self):
        self.manager = di.SingletonPerThreadComponentInstancesManager()
        self.container = di.Container()
        self.container.components[SimpleComponent] = SimpleComponent
        
    def test_current_thread(self):
        obj = self.manager.get_instance(self.container, SimpleComponent)
        assert isinstance(obj, SimpleComponent)
        
    def test_50_threads(self):
        lis = []
        
        class AnotherThread(Thread):
            def __init__(self, manager, container, lis):
                super(AnotherThread, self).__init__()
                self.container = container
                self.manager = manager
                self.lis = lis
                self.error = None
                
            def run(self):
                try:
                    obj = self.manager.get_instance(self.container, SimpleComponent)
                    assert isinstance(obj, SimpleComponent)
                    
                    obj2 = self.manager.get_instance(self.container, SimpleComponent)
                    assert isinstance(obj2, SimpleComponent)
                    
                    assert obj == obj2
                    
                    self.lis.append(obj)
                    
                except Exception as e:
                    self.error = e
                    raise
                
        ths = []
        
        for k in range(50):
            t = AnotherThread(self.manager, self.container, lis)
            ths.append(t)
            t.start()
            
        rg = range(len(ths))
        
        while 1:
            bk = False
            
            for n in rg:
                if not ths[n].is_alive():
                    bk = True
                    
            if bk:
                break
        
        for n in rg:
            if ths[n].error:
                raise ths[n].error
            
        self.assertEqual(len(set(lis)), len(lis))

###########################################################
# Concurrency Singleton Component Instances Manager Tests #
###########################################################

class ConcurrencySingletonComponentInstancesManagerTest(TestCase):
    def setUp(self):
        self.manager = di.ConcurrencySingletonComponentInstancesManager()
        self.container = di.Container()
        self.container.components[SimpleComponent] = SimpleComponent
        
    def test_current_thread(self):
        obj = self.manager.get_instance(self.container, SimpleComponent)
        assert isinstance(obj, SimpleComponent)
        
    def test_50_threads(self):
        lis = []
        
        class AnotherThread(Thread):
            def __init__(self, manager, container, lis):
                super(AnotherThread, self).__init__()
                self.container = container
                self.manager = manager
                self.lis = lis
                self.error = None
                
            def run(self):
                try:
                    obj = self.manager.get_instance(self.container, SimpleComponent)
                    assert isinstance(obj, SimpleComponent)
                    
                    obj2 = self.manager.get_instance(self.container, SimpleComponent)
                    assert isinstance(obj2, SimpleComponent)
                    
                    assert obj == obj2
                    
                    self.lis.append(obj)
                    
                except Exception as e:
                    self.error = e
                    raise
                
        ths = []
        
        for k in range(50):
            t = AnotherThread(self.manager, self.container, lis)
            ths.append(t)
            t.start()
            
        rg = range(len(ths))
        
        while 1:
            bk = False
            
            for n in rg:
                if not ths[n].is_alive():
                    bk = True
                    
            if bk:
                break
        
        for n in rg:
            if ths[n].error:
                raise ths[n].error
            
        # Singleton is a Unique Instance
        self.assertEqual(len(set(lis)), 1)

if __name__ == "__main__":
    unittest.main()
