'''
Python Container Of Dependency Injection implementation

Created on Sep 25, 2012

@author: Moises P. Sena <moisespsena@gmail.com>
'''

from threading import Lock
from inspect import isclass

def import_class(module_name, class_name=None):
    components = module_name.split('.')
    
    if not class_name:
        class_name = components[len(components) - 1:][0]
        components = components[:len(components) - 1]
        mod = __import__('.'.join(components))
    else:
        mod = __import__(module_name)
    
    components.append(class_name)
    
    for comp in components[1:]:
        mod = getattr(mod, comp)
        
    assert isclass(mod)
    return mod

class decorators(dict): pass

class decorator(object):
    def __call__(self, fn, keys=()):
        keys = set(keys + (self.__class__,))
            
        if not hasattr(fn, 'decorators'):
            fn.decorators = decorators()
        
        for key in keys:
            fn.decorators[key] = self
            
        return fn
    
    @staticmethod
    def of(fn, key):
        if hasattr(fn, 'decorators'):
            decs = fn.decorators
            
            if key in decs:
                dec = decs[key]
                return dec
            
        return None

class InstanceFactory(object):
    def get_instance(self, **kwargs):
        pass

class ScopeRegistry(object):
    def __init__(self):
        self.scopes = dict()
        
    def set(self, key, manager):
        self.scopes[key] = manager
        
    def get(self, key):
        return self.scopes[key]
    
    def __getitem__(self, key):
        return self.get(key)
    
    def __setitem__(self, key, value):
        return self.set(key, value)
    
    def __contains__(self, key):
        return self.has(key)
    
    def has(self, key):
        return self.scopes[key]

def create_instance(cls, *args, **params):
    if issubclass(ClosureAttrProxy, cls.__init__.__class__):
        obj = cls.__new__(cls)
        cls.__init__(obj, *args, **params)
    else:
        obj = cls(*args, **params)
    
    if hasatt(obj, 'post_init'):
        obj.post_init()
        
    return obj

class SimpleInstanceCreator(object):
    def create_instance(self, container, cls, *args, **params):
        params['container'] = container
        return create_instance(cls, **params)

class ComponentInstancesManager(object):
    def get_instance(self, cls, **params):
        raise NotImplementedError()
    
    def create_instance(self, container, cls, *args, **params):
        if comp.by(cls): 
            params['container'] = container
            obj = create_instance(cls, *args, **params)
        else:
            obj = cls(*args, **params)
        
        if hasatt(obj, 'post_init'):
            obj.post_init()
                
        return obj
    
class SingletonComponentInstancesManager(ComponentInstancesManager):
    def __init__(self):
        self.instances = dict()
        
    def get_instance(self, container, cls, **params):
        if not cls in self.instances:
            self.instances[cls] = self.create_instance(container, cls, **params)
            
        return self.instances[cls]
    
class ConcurrencySingletonComponentInstancesManager(SingletonComponentInstancesManager):
    def __init__(self):
        super(ConcurrencySingletonComponentInstancesManager, self).__init__()
        self.lock = Lock()
        
    def get_instance(self, container, cls, **params):
        if not cls in self.instances:
            with self.lock:
                if not cls in self.instances:
                    instance = self.create_instance(container, cls, **params)
                    self.instances[cls] = instance
                    return instance
            
        return self.instances[cls]
    
class PrototypeComponentInstancesManager(ComponentInstancesManager):
    def get_instance(self, container, cls, **params):
        return self.create_instance(container, cls, **params)

class RequestComponentInstancesManager(ComponentInstancesManager):
    def get_instance(self, container, cls, **params):
        return self.create_instance(container, cls, **params)
    

class SessionComponentInstancesManager(ComponentInstancesManager):
    def get_instance(self, container, cls, **params):
        return self.create_instance(container, cls, **params)
    

class Scope(object): pass
class Singleton(Scope): pass
class Prototype(Scope): pass

class Container(object):
    def __init__(self):
        self.scopes = ScopeRegistry()
        self.components = ComponentRegistry(Prototype)
        self.simple_instance_creator = SimpleInstanceCreator()
        self.global_components = {
                                  '@Container' : self,
                                  '@Components' : self.components,
                                  '@Scopes': self.scopes }
        self._init_scopes()
        
    def _init_scopes(self):
        self.scopes[Singleton] = SingletonComponentInstancesManager()
        self.scopes[Prototype] = PrototypeComponentInstancesManager()

    def is_component(self, key):
        if key in self.global_components:
            return True
        return self.components.is_component(key)
    
    def component_instance(self, key):
        if key in self.global_components:
            obj = self.global_components[key]
        elif self.components.is_component(key):
            component = self.components.get(key)
            instance_manager = self.instance_manager(component.scope)
            obj = instance_manager.get_instance(self, component.cls, **component.deps)
            
            if component.factory:
                obj = obj.instance
        else:
            raise Exception("CDI Component '%s' not exists" % key)    
            
        return obj
        
    def instance_manager(self, scope):
        manager = self.scopes.get(scope)
        return manager
    
    def dependencies_instances(self, **kwargs):
        for k in kwargs:
            dep = kwargs[k]
                
            if is_dependency_obj(dep):
                dep = self.instance_for(dep.key)
                kwargs[k] = dep
        return kwargs
    
    def dependencies_instances_none(self, **kwargs):
        for k in kwargs:
            dep = kwargs[k]
                
            if is_dependency_obj(dep):
                kwargs[k] = None
        return kwargs
    
    def instance_for(self, key_or_class, **kwargs):
        if self.is_component(key_or_class):
            return self.component_instance(key_or_class)
        elif not isclass(key_or_class):
            raise Exception("CDI Component '%s' not exists" % key_or_class)
        else:
            obj = self.simple_instance_creator.create_instance(self, key_or_class)
            return obj

class Component(object):
    def __init__(self, key, cls, scope, deps, factory):
        self.key = key
        self.cls = cls
        self.scope = scope
        self.deps = deps
        self.factory = factory

class Dependency(object):
    def __init__(self, registry, key):
        self.__registry = registry
        self.key = key
        
    def __getattr__(self, name):
        component = self.__registry.get(self.key)
        attr = getattr(component, name)
        return attr
        
    def __hasattr__(self, name):
        component = self.__registry.get(self.key)
        attr = hasattr(component, name)
        return attr
    
def is_dependency_obj(obj):
    return isinstance(obj, Dependency)
    
def is_component_obj(obj):
    return isinstance(obj, Component)

class ComponentRegistry(object):
    def __init__(self, default_scope):
        self.components = dict()
        self.components_cls = dict()
        self.default_scope = default_scope
        
    def is_component(self, key_or_cls):
        if not key_or_cls in self.components:
            if not key_or_cls in self.components_cls:
                return False
        return True
        
    def register(self, key, cls):
        cm = comp.by(cls)
        if not cm:
            raise Exception("The class %s does not have be decorated of @comp" % cls)
        
        if key in self.components:
            del self.components_cls[self.components[key].cls]
        
        c = Component(key, cls, cm.scope if cm.scope else self.default_scope, cm.dependencies, cm.factory)
        self.components[key] = c
        self.components_cls[cls] = c
        
    def get(self, key_or_cls):
        if key_or_cls in self.components:
            return self.components[key_or_cls]
        return self.components_cls[key_or_cls]
    
    def __setitem__(self, key, cls):
        self.register(key, cls)
    
    def __getitem__(self, key):
        return self.get(key)
    
    def __contains__(self, key):
        return self.is_component(key)

def hasatt(obj, name):
    if not hasattr(obj, name):
        if not hasattr(obj, 'proxy'):
            return False
        if not hasattr(obj.proxy.current, name):
            return hasattr(obj.proxy.original, name)
    return True

def getatt(obj, name):
    if not hasattr(obj, name):
        if hasattr(obj, 'proxy'):
            return getatt(obj.proxy, name)
    return getattr(object, name)

def setatt(obj, name, value):
    if not hasattr(obj, name):
        if hasattr(obj, 'proxy'):
            setatt(obj.proxy, name, value)
            return
    setattr(object, name, value)

def closure_attr_proxy(original, current):
    cap = ClosureAttrProxy(original, current)
    def closure_attr_proxy_method(self, *args, **kwargs):
        return cap(self, *args, **kwargs)
    closure_attr_proxy_method.proxy = cap
    return closure_attr_proxy_method

def is_closure_attr_proxy(fn):
    if hasattr(fn, 'proxy'):
        if isinstance(fn.proxy, ClosureAttrProxy):
            return True
    return False

class ClosureAttrProxy(object):
    def __init__(self, original, current):
        object.__setattr__(self, 'original', original)
        object.__setattr__(self, 'current', current)
        
    def __hasattr__(self, name):
        if not hasattr(self.current, name):
            return hasattr(self.original, name)
        return False
    
    def __getattr__(self, name):
        return getattr(self.original, name)
    
    def __setattr__(self, name, value):
        return setattr(self.original, name, value)
    
    def __call__(self, *args, **kwargs):
        return self.current(*args, **kwargs)

class comp(decorator):
    def __init__(self, scope=None, deps=dict(), factory=False):
        super(comp, self).__init__()
        self.scope = scope
        self.deps = deps
        self.init = None
        self.dependencies = None
        self.factory = factory
        self.deps_none = None
    
    def __call__(self, cls, keys=()):
        cls = super(comp, self).__call__(cls, keys=(comp,) + keys)
        
        dependencies = dict()
        self.deps_none = dict()
        
        for k in self.deps:
            dependencies[k] = Dependency(self, self.deps[k])
            self.deps_none[k] = None
        
        self.dependencies = dependencies
        self.init = cls.__init__
        fn = init(**self.deps)
        
        def comp_init(*args, **kwargs):
            return self.init(*args, **kwargs)
        
        fn = fn(comp_init)
        cls.__init__ = fn
        return cls
    
    @staticmethod
    def by_init(fn):
        return comp.by(fn.im_class)
    
    @staticmethod
    def by(cls):
        return decorator.of(cls, comp)
        
class inject(decorator):
    def __init__(self, **deps):
        super(inject, self).__init__()
        self.deps = deps
        self.fn = None
    
    def container_for(self, kwargs):
        if 'container' in kwargs:
            container = kwargs['container']
            del kwargs['container']
            return container
        return None
    
    def invoke(self, obj, container, *args, **kwargs):
        if container:
            params = container.dependencies_instances(**kwargs)
            
            for k in self.deps:
                if not k in params:
                    dep = self.deps[k]
                    dep = container.instance_for(dep)
                    params[k] = dep
        else:
            params = kwargs
            
        return self.fn(obj, *args, **params)
    
    def create_closure(self):
        def injected_method(obj, *args, **kwargs):
            container = self.container_for(kwargs)
            if not container and hasattr(obj, '_ioc_container'):
                container = obj._ioc_container
            return self.invoke(obj, container, *args, **kwargs)
        return injected_method
    
    def __call__(self, fn, keys=()):
        self.fn = super(inject, self).__call__(fn, keys=(inject,) + keys)
        closure = self.create_closure()
        closure = closure_attr_proxy(self.fn, closure)
        return closure
    
class init(inject):
    def create_closure(self):
        def injected_init(obj, *args, **kwargs):
            container = self.container_for(kwargs)
            obj._ioc_container = container
            return self.invoke(obj, container, *args, **kwargs)
        injected_init.injected_init = True
        return injected_init
    
class Factory():
    def get_instance(self):
        raise NotImplementedError()
    
    instance = property(lambda self: self.get_instance())
