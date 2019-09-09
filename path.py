import operator as op
import typing
import itertools
import collections


def first(it, default=None, pred=None):
    return next((x for x in it if pred is None or pred(x)), default)


def last(it, default=None, pred=None):    
    return next(iter(collections.deque((x for x in it if pred is None or pred(x)), maxlen=1)), default)


class InvalidPath(ValueError):
    def __init__(self, path, obj):
        super().__init__(f"Invalid path {path} for object {obj}")
        self.path = path
        self.obj = obj

T = typing.TypeVar("T")
        
class Path(tuple):
    def __new__(cls, *components):
        return tuple.__new__(cls, components)

    def __repr__(self):
        components = ", ".join(map(repr, self))
        return f"{type(self).__name__}({components})"

    @classmethod
    def _getter(cls, cwd: T, c: str) -> T:
        raise NotImplementedError

    def follow(self, obj):
        cwd = obj
        for c in self:
            cwd = self._getter(cwd, c)
            yield cwd

    def follow_or(self, obj, default):
        cwd = obj
        try:
            yield from self.follow(obj)
        except InvalidPath:
            yield default

    def __add__(self, other):
        return PathChain(self, other)

    def prepend(self, c: str):
        return type(self)(c, *self)

    def append(self, c: str):
        return type(self)(*self, c)

    def __truediv__(self, c: str):
        return self.append(c)

    def __rtruediv__(self, c: str):
        return self.prepend(c)
    

class PathChain(Path):
    def __new__(cls, *paths: Path):
        return tuple.__new__(cls, (t(*itertools.chain.from_iterable(g)) for t, g in itertools.groupby(paths, type)))

    def follow(self, obj):
        cwd = obj
        for subpath in self:
            for cwd in subpath.follow(cwd):
                yield cwd

            
class AttrPath(Path):
    def __str__(self):
        return "$." + ".".join(self)

    @classmethod
    def from_str(cls, path: str):
        return cls(*path.lstrip("$.").split("."))

    def _getter(self, obj, at):
        try:
            return getattr(obj, at)
        except AttributeError as ex:
            raise InvalidPath(self, obj) from ex


class KeyPath(Path):
    def __str__(self):
        return "$:" + ":".join(map(repr, self))

    @classmethod
    def from_str(cls, path: str):
        return cls(*path.lstrip("$:").split(":"))

    def _getter(self, obj, at):
        try:
            return obj[at]
        except KeyError as ex:
            raise InvalidPath(self, obj) from ex
        
        
def identity(x):
    return x
                   

def cd(obj: typing.Any, path: Path) -> typing.Any:
    return last(path.follow(obj))


class Attribute(typing.NamedTuple):
    name: str
    value: typing.Any
    

class Key(typing.NamedTuple):
    name: str
    value: typing.Any


class Cursor(typing.NamedTuple):
    track: typing.Sequence[typing.Tuple[str, typing.Any]]
    destination: Path
    
    def back(self):
        if self.track:
            return Cursor(
                track=self.track[:-2],
                destination=self.destination.prepend(self.track[-1][0])
            )
        else:
            # TODO: raise appropriate custom error
            raise ValueError

    def forward(self):
        if self.track and self.destination:
            return Cursor(
                track=(*self.track, (self.destination[0], next(self.destination.follow(self.track[-1][1])))),
                destination=self.destination.prepend(self.track[-1][0])
            )
        else:
            # TODO: raise appropriate custom error
            raise ValueError

    def get(self):
        return self.track[-1][1]

    def __str__(self):
        return f"{type(self).__name__}(focus={self.track})"
