# -*- coding: utf-8 -*-
#
# Client for a schoollibrary-server.
# Copyright (c) 2014 Niklas Fiekas <niklas.fiekas@tu-clausthal.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import collections
import operator
import sys

try:
    from reprlib import recursive_repr
except ImportError:
    try:
        from thread import get_ident
    except ImportError:
        from dummy_thread import get_ident

    # Backport copied from cpython/Lib/reprlib.py.
    def recursive_repr(fillvalue='...'):
        'Decorator to make a repr function return fillvalue for a recursive call'

        def decorating_function(user_function):
            repr_running = set()

            def wrapper(self):
                key = id(self), get_ident()
                if key in repr_running:
                    return fillvalue
                repr_running.add(key)
                try:
                    result = user_function(self)
                finally:
                    repr_running.discard(key)
                return result

            # Can't use functools.wraps() here because of bootstrap issues
            wrapper.__module__ = getattr(user_function, '__module__')
            wrapper.__doc__ = getattr(user_function, '__doc__')
            wrapper.__name__ = getattr(user_function, '__name__')
            wrapper.__annotations__ = getattr(user_function, '__annotations__', {})
            return wrapper

        return decorating_function

class IndexedOrderedDict(dict):
    """A dictionary that is indexed by insertion order."""

    def __init__(self, *args, **kwds):
        """
        Initialize an ordered dictionary.  The signature is the same as
        regular dictioneries, but keywords arguments are not recommended because
        their insertion order is arbitrary.
        """
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))

        self._map = []
        self.__update(*args, **kwds)

    def __setitem__(self, key, value, dict_setitem=dict.__setitem__):
        """iod.__setitem__(i, y) <==> iod[i] = y"""
        if key not in self:
            self._map.append(key)
        dict_setitem(self, key, value)

    def __delitem__(self, key, dict_delitem=dict.__delitem__):
        """iod.__delitem__(y) <==> del iod[y]"""
        dict_delitem(self, key)
        self._map.remove(key)

    def __iter__(self):
        """iod.__iter__() <==> iter(iod)"""
        return self._map.__iter__()

    def __reversed__(self):
        """iod.__reversed__() <==> reversed(iod)"""
        return self._map.__reversed__()

    def clear(self):
        """iod.clear() -> None.  Remove all items from iod."""
        self._map[:] = []
        dict.clear(self)

    def popitem(self, last=True):
        """
        iod.popitem() -> (k, v), return and remove a (key, value) pair.
        Pairs are returned LIFO order if last is true or FIFI order if false.
        """
        key = self._map.pop() if last else self._map.pop(0)
        value = dict.pop(self, key)
        return key, value

    def move_to_end(self, key, last=True):
        """
        Move an existing element to the end (or beginning if last==False).

        Raises KeyError if the element does not exist.
        When last=True, acts like a faster version of self[key]=self.pop(key).
        """
        self._map.remove(key)
        if last:
            self._map.append(key)
        else:
            self._map.insert(0, key)

    def __sizeof__(self):
        return sys.getsizeof(self.__dict__) + sys.getsizeof(self._map)

    update = __update = collections.MutableMapping.update
    __ne__ = collections.MutableMapping.__ne__

    def keys(self):
        return IndexedKeysView(self)

    keysview = keys

    def values(self):
        return IndexedValuesView(self)

    valuesview = values

    def items(self):
        return IndexedItemsView(self)

    itemsview = items

    __marker = object()

    def pop(self, key, default=__marker):
        """
        iod.pop(k[,d]) -> v, remove specified key and return the corresponding
        value.  If key is not found, d is returned if given, otherwise KeyError
        is raised.
        """
        if key in self:
            result = self[key]
            del self[key]
            return result
        if default is self.__marker:
            raise KeyError(key)
        return default

    def setdefault(self, key, default=None):
        """
        iod.setdefault(k[,d]) -> od.get(k,d), also set od[k]=d if k not in d
        """
        if key in self:
            return self[key]
        self[key] = default
        return default

    @recursive_repr()
    def __repr__(self):
        """iod.__repr__() <==> repr(iod)"""
        if not self:
            return '%s()' % (self.__class__.__name__, )
        return '%s(%r)' % (self.__class__.__name__, list(self.items()))

    def __reduce__(self):
        """Return state information for pickling"""
        inst_dict = vars(self).copy()
        for k in vars(IndexedOrderedDict()):
            inst_dict.pop(k, None)
        return self.__class__, (), inst_dict or None, None, iter(self.items())

    def copy(self):
        """od.copy() -> a shallow copy of iod"""
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        """
        IOD.fromkeys(S[,v]) -> New indexed ordered dictionary with keys from S.
        If not specified, the value defaults to None.
        """
        self = cls()
        for key in iterable:
            self[key] = value
        return self

    def __eq__(self, other):
        """
        iod.__eq__(y) <==> iod==y.  Comparison to another IOD is
        order-sensitive while comparison to a regular mapping is
        order-insensitive.
        """
        if isinstance(other, collections.OrderedDict) or isinstance(other, IndexedOrderedDict):
            return dict.__eq__(self, other) and all(map(operator.eq, self, other))
        return dict.__eq__(self, other)


class IndexedKeysView(collections.KeysView):

    def __getitem__(self, index):
        return self._mapping._map[index]

    def index(self, x):
        return self._mapping._map.index(x)


class IndexedValuesView(collections.ValuesView):

    def __getitem__(self, index):
        key = self._mapping._map[index]
        return self._mapping[key]


class IndexedItemsView(collections.ItemsView):

    def __getitem__(self, index):
        key = self._mapping._map[index]
        return key, self._mapping[key]
