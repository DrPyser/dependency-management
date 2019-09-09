"""
Dependency management implementation.
* Dependency graph to model dependency relationships between entities and code components
* Automatic extraction of dependency relationships through signature inspection(type annotations, default values)

Goals/Todos:
* easily declare dependencies between code components with minimal boilerplate, maximum flexibility
* inspectable dependency graph
* runtime provider: interface to provide a component(instance), automatically resolving and instantiating dependencies
  (provide A -> resolve A deps -> provide A deps -> ...)
* namespaces: dependency relationships are namespaced, such that EntityA.dep1 != EntityB.dep1, 
  even if both dependencies are specified identically. 
* provider scope, shared dependencies, ability to provide dependency objects with different scoping: global (shared) singleton, per-type, per-thread, ... 

"""
import typing
import inspect
import collections
import types


T = typing.TypeVar("T")

# move to utils
def first(it, default=None, pred=None):
    return next((x for x in it if pred is None or pred(x)), default)


# move to utils
def record_init(self, *args, **kwargs):
    slots = getattr(type(self), "__slots__")
    for a, k in zip(args, slots):
        setattr(self, k, a)
        
    for k, v in kwargs.items():
        setattr(self, k, v)

# move to utils
def record_repr(self):
    type_name = type(self).__name__
    slots = getattr(type(self), "__slots__")
    field_string = ", ".join(
        k+"="+str(getattr(self, k))
        for k in slots
    )
    return f"{type_name}({field_string})"
            
# move to utils
def record_type(name, bases, nmspc, **kwargs):
    annotations = nmspc.get("__annotations__", {})
    slots = list(annotations.keys())
    nmspc.update(__slots__=slots, __init__=record_init, __repr__=record_repr)
    return types.new_class(name, bases, exec_body=lambda ns: ns.update(nmspc), kwds=kwargs)


# move to utils
class RecordType(type):
    def __new__(cls, name, bases, nmspc, **kwargs):
        print(cls, name, bases, nmspc, kwargs)
        annotations = nmspc.get("__annotations__", {})
        slots = list(annotations.keys())
        nmspc.update(__slots__=slots, __init__=record_init, __repr__=record_repr)
        return type.__new__(cls, name, bases, nmspc, **kwargs)


# move to utils
class RecordBase(metaclass=RecordType):
    __init__ = record_init
    __repr__ = record_repr
    


# move to utils
def subclass(parent: typing.Type[T], name: str, exec_body=None, mixins: tuple=(), **kwargs) -> typing.Type[T]:
    return types.new_class(name, bases=(*mixins, parent), kwds=kwargs, exec_body=exec_body)


# move to utils
class delegate:
    def __init__(self, source, name=None):
        self.source = source
        self.name = name
        self.target = name and getattr(source, name)

    def __set_name__(self, name):
        if self.name is None:
            self.name = name
            self.target = getattr(self.source, self.name)

    def __get__(self, instance, owner):
        return self.target.__get__(instance, owner)

    

class Dependency(typing.Generic[T], RecordBase):
    factory: typing.Callable[..., T]
    type: typing.Type[T]

    def provide(self, *args, **kwargs) -> T:
        return self.factory(*args, **kwargs)
    
    
class Node(typing.Generic[T], metaclass=RecordType):
    name: str
    dependency_type: Dependency[T]


# TODO: look into using algebraic graph impl.: dep = connect (vertex Dependency) (overlay [Dependency ...])
class DepGraph:
    def __init__(self):
        self.type_index: typing.Dict[type, typing.Set[Node]] = collections.defaultdict(set)
        self.name_index: typing.Dict[str, Node] = {}
        # Invariant: set.union(*self.type_index.values()) == set(self.name_index.values())

        self.relationships: typing.Set[typing.Tuple[Node, Node]] = set()
        # Invariant: set().union(*self.relationships.values()) == set(self.name_index.values())

    def add_node(self, dep: Node, dependencies=None):
        if dep.name not in self.name_index:
            self.type_index[dep.dependency_type.type].add(dep)
            self.name_index[dep.name] = dep
        else:
            # Probably should log something, or return some special value
            ...

        if dependencies:
            for d in dependencies:
                self.add_node(d)
                self.relationships.add(
                    (dep, d)
                )

    def add_dependencies(self, name: str, dependencies: typing.Set[Node]):
        node = self.name_index[name]
        for d in dependencies:
            self.relationships.add(
                (node, d)
            )

    def add_relationship(self, dependent: str, dependence: str):
        assert dependent in self.name_index
        assert dependence in self.name_index
        self.relationships.add((self.name_index[dependent], self.name_index[dependence]))

    def get_by_name(self, name: str):
        return self.name_index[name]

    def get_dependents(self, name: str):
        node = self.name_index[name]
        dependents = set(
            dt
            for dt, dc in self.relationships
            if dc is node
        )
        return dependents

    def get_dependencies(self, name: str):
        node = self.name_index[name]
        dependencies = set(
            dc
            for dt, dc in self.relationships
            if dt is node
        )
        return dependencies
    

def extract_dependencies(dependent: typing.Callable) -> typing.Dict[str, Dependency]:
    """
    Given a callable(usually class or function), identify dependencies
    by looking at attributes or signature
    """
    if hasattr(dependent, "__dependencies__"):
        return dependent.__dependencies__
    else:
        dependent_sig = inspect.signature(dependent)
        deps: typing.Dict[str, Dependency] = {
            p_name: Dependency(type=p.annotation, factory=p.default.factory if isinstance(p.default, Dependency) else p.annotation)
            for p_name, p in dependent_sig.parameters.items()
        }
        return deps


    
    
# class Balh:
#     def __init__(self, a: A, b: B):
#         ...

# class DependencyManager:
#     def register(self, dependency: DependencyProfile):
#         ...

#     def provide_type(self, klass: typing.Type[T]) -> T:
#         ...

#     def provide_dependency()
