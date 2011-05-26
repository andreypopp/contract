# -*- coding: utf-8 -*-

import functools
import inspect

"""
Contract is tiny library for data validation
It provides several primitives to validate complex data structures
Look at doctests for usage examples
"""

__all__ = ("ContractValidationError", "Contract", "AnyC", "IntC", "StringC",
           "ListC", "DictC", "OrC", "NullC", "FloatC", "EnumC", "CallableC",
           "CallC", "ForwardC", "BoolC", "guard", )


class ContractValidationError(TypeError):
    
    """
    Contract validation error
    """
    
    def __init__(self, msg, name=None, errors=None):
        self.msg = msg
        self.name = name
        self.errors = errors
        super(ContractValidationError, self).__init__(self.formatted)

    @property
    def formatted(self):
        message = self.msg
        if self.name:
            message = "%s: %s" % (self.name, message)
        if self.errors:
            message = "%s: %s" % (message, [x.args[0] for x in self.errors])
        return message



class ContractMeta(type):
    
    """
    Metaclass for contracts to make using "|" operator possible not only
    on instances but on classes
    
    >>> IntC | StringC
    <OrC(<IntC>, <StringC>)>
    >>> IntC | StringC | NullC
    <OrC(<IntC>, <StringC>, <NullC>)>
    """
    
    def __or__(cls, other):
        return cls() | other


class Contract(object):
    
    """
    Base class for contracts, provides only one method for
    contract validation failure reporting
    """
    
    __metaclass__ = ContractMeta
    
    def check(self, value):
        """
        Implement this method in Contract subclasses
        """
        cls = "%s.%s" % (type(self).__module__, type(self).__name__)
        raise NotImplementedError("method check is not implemented in"
                                  " '%s'" % cls)
    
    def _failure(self, message):
        """
        Shortcut method for raising validation error
        """
        raise ContractValidationError(message)
    
    def _contract(self, contract):
        """
        Helper for complex contracts, takes contract instance or class
        and returns contract instance
        """
        if isinstance(contract, Contract):
            return contract
        elif issubclass(contract, Contract):
            return contract()
        else:
            raise RuntimeError("%r should be instance or subclass"
                               " of Contract" % contract)
    
    def __or__(self, other):
        return OrC(self, other)


class AnyC(Contract):
    
    """
    >>> AnyC()
    <AnyC>
    >>> AnyC().check(object())
    """
    
    def check(self, value):
        pass
    
    def __repr__(self):
        return "<AnyC>"


class OrCMeta(ContractMeta):
    
    """
    Allows to use "<<" operator on OrC class
    
    >>> OrC << IntC << StringC
    <OrC(<IntC>, <StringC>)>
    """
    
    def __lshift__(cls, other):
        return cls() << other


class OrC(Contract):
    
    """
    >>> nullString = OrC(StringC, NullC)
    >>> nullString
    <OrC(<StringC>, <NullC>)>
    >>> nullString.check(None)
    >>> nullString.check("test")
    >>> nullString.check(1)
    Traceback (most recent call last):
    ...
    ContractValidationError: no one contract matches
    """
    
    __metaclass__ = OrCMeta
    
    def __init__(self, *contracts):
        self.contracts = map(self._contract, contracts)
    
    def check(self, value):
        for contract in self.contracts:
            try:
                contract.check(value)
            except ContractValidationError:
                pass
            else:
                return
        self._failure("no one contract matches")
    
    def __lshift__(self, contract):
        self.contracts.append(self._contract(contract))
        return self
    
    def __or__(self, contract):
        self << contract
        return self
    
    def __repr__(self):
        return "<OrC(%s)>" % (", ".join(map(repr, self.contracts)))


class NullC(Contract):
    
    """
    >>> NullC()
    <NullC>
    >>> NullC().check(None)
    >>> NullC().check(1)
    Traceback (most recent call last):
    ...
    ContractValidationError: value should be None
    """
    
    def check(self, value):
        if value is not None:
            self._failure("value should be None")
    
    def __repr__(self):
        return "<NullC>"


class BoolC(Contract):
    
    """
    >>> BoolC()
    <BoolC>
    >>> BoolC().check(True)
    >>> BoolC().check(False)
    >>> BoolC().check(1)
    Traceback (most recent call last):
    ...
    ContractValidationError: value should be True or False
    """
    
    def check(self, value):
        if not isinstance(value, bool):
            self._failure("value should be True or False")
    
    def __repr__(self):
        return "<BoolC>"


class NumberCMeta(ContractMeta):
    
    """
    Allows slicing syntax for min and max arguments for
    number contracts
    
    >>> IntC[1:]
    <IntC(min=1)>
    >>> IntC[1:10]
    <IntC(min=1, max=10)>
    >>> IntC[:10]
    <IntC(max=10)>
    >>> FloatC[1:]
    <FloatC(min=1)>
    """
    
    def __getitem__(self, slice_):
        return self(min_=slice_.start, max_=slice_.stop)


class IntC(Contract):
    
    """
    >>> IntC()
    <IntC>
    >>> IntC(min_=1)
    <IntC(min=1)>
    >>> IntC(max_=10)
    <IntC(max=10)>
    >>> IntC(min_=1, max_=10)
    <IntC(min=1, max=10)>
    >>> IntC().check("foo")
    Traceback (most recent call last):
    ...
    ContractValidationError: value is not int
    >>> IntC(min_=1).check(1)
    >>> IntC(min_=2).check(1)
    Traceback (most recent call last):
    ...
    ContractValidationError: value is less than 2
    >>> IntC(max_=10).check(5)
    >>> IntC(max_=3).check(5)
    Traceback (most recent call last):
    ...
    ContractValidationError: value is greater than 3
    """
    
    __metaclass__ = NumberCMeta
    
    def __init__(self, min_=None, max_=None):
        self.min = min_
        self.max = max_
    
    def check(self, value):
        if not isinstance(value, int):
            self._failure("value is not int")
        if self.min is not None and value < self.min:
            self._failure("value is less than %s" % self.min)
        if self.max is not None and value > self.max:
            self._failure("value is greater than %s" % self.max)
    
    def __repr__(self):
        r = "<IntC"
        options = []
        if self.min is not None:
            options.append("min=%s" % self.min)
        if self.max is not None:
            options.append("max=%s" % self.max)
        if options:
            r += "(%s)" % (", ".join(options))
        r += ">"
        return r


class FloatC(Contract):
    
    """
    >>> FloatC()
    <FloatC>
    >>> FloatC(min_=1)
    <FloatC(min=1)>
    >>> FloatC(max_=10)
    <FloatC(max=10)>
    >>> FloatC(min_=1, max_=10)
    <FloatC(min=1, max=10)>
    >>> FloatC().check(1.0)
    >>> FloatC().check(1)
    Traceback (most recent call last):
    ...
    ContractValidationError: value is not float
    >>> FloatC(min_=2).check(3.0)
    >>> FloatC(min_=2).check(1.0)
    Traceback (most recent call last):
    ...
    ContractValidationError: value is less than 2
    >>> FloatC(max_=10).check(5.0)
    >>> FloatC(max_=3).check(5.0)
    Traceback (most recent call last):
    ...
    ContractValidationError: value is greater than 3
    """
    
    __metaclass__ = NumberCMeta
    
    def __init__(self, min_=None, max_=None):
        self.min = min_
        self.max = max_
    
    def check(self, value):
        if not isinstance(value, float):
            self._failure("value is not float")
        if self.min is not None and value < self.min:
            self._failure("value is less than %s" % self.min)
        if self.max is not None and value > self.max:
            self._failure("value is greater than %s" % self.max)
    
    def __repr__(self):
        r = "<FloatC"
        options = []
        if self.min is not None:
            options.append("min=%s" % self.min)
        if self.max is not None:
            options.append("max=%s" % self.max)
        if options:
            r += "(%s)" % (", ".join(options))
        r += ">"
        return r


class StringC(Contract):
    
    """
    >>> StringC()
    <StringC>
    >>> StringC(allow_blank=True)
    <StringC(blank)>
    >>> StringC().check("foo")
    >>> StringC().check("")
    Traceback (most recent call last):
    ...
    ContractValidationError: blank value is not allowed
    >>> StringC(allow_blank=True).check("")
    >>> StringC().check(1)
    Traceback (most recent call last):
    ...
    ContractValidationError: value is not string
    """
    
    def __init__(self, allow_blank=False):
        self.allow_blank = allow_blank
    
    def check(self, value):
        if not isinstance(value, basestring):
            self._failure("value is not string")
        if not self.allow_blank and len(value) is 0:
            self._failure("blank value is not allowed")
    
    def __repr__(self):
        return "<StringC(blank)>" if self.allow_blank else "<StringC>"


class SquareBracketsMeta(ContractMeta):
    
    """
    Allows usage of square brackets for ListC initialization
    
    >>> ListC[IntC]
    <ListC(<IntC>)>
    >>> ListC[IntC, 1:]
    <ListC(min_length=1 | <IntC>)>
    >>> ListC[:10, IntC]
    <ListC(max_length=10 | <IntC>)>
    >>> ListC[1:10]
    Traceback (most recent call last):
    ...
    RuntimeError: Contract is required for ListC initialization
    """
    
    def __getitem__(self, args):
        slice_ = None
        contract = None
        if not isinstance(args, tuple):
            args = (args, )
        for arg in args:
            if isinstance(arg, slice):
                slice_ = arg
            elif isinstance(arg, Contract) or issubclass(arg, Contract):
                contract = arg
        if not contract:
            raise RuntimeError("Contract is required for ListC initialization")
        if slice_:
            return self(contract, min_length=slice_.start or 0,
                                  max_length=slice_.stop)
        return self(contract)


class ListC(Contract):
    
    """
    >>> ListC(IntC)
    <ListC(<IntC>)>
    >>> ListC(IntC, min_length=1)
    <ListC(min_length=1 | <IntC>)>
    >>> ListC(IntC, min_length=1, max_length=10)
    <ListC(min_length=1, max_length=10 | <IntC>)>
    >>> ListC(IntC).check(1)
    Traceback (most recent call last):
    ...
    ContractValidationError: value is not list
    >>> ListC(IntC).check([1, 2, 3])
    >>> ListC(StringC).check(["foo", "bar", "spam"])
    >>> ListC(IntC).check([1, 2, 3.0])
    Traceback (most recent call last):
    ...
    ContractValidationError: can't validate: ['2: value is not int']
    >>> ListC(IntC, min_length=1).check([1, 2, 3])
    >>> ListC(IntC, min_length=1).check([])
    Traceback (most recent call last):
    ...
    ContractValidationError: can't validate: ['list length is less than 1']
    >>> ListC(IntC, max_length=2).check([1, 2])
    >>> ListC(IntC, max_length=2).check([1, 2, 3])
    Traceback (most recent call last):
    ...
    ContractValidationError: can't validate: ['list length is greater than 2']
    """
    
    __metaclass__ = SquareBracketsMeta
    
    def __init__(self, contract, min_length=0, max_length=None):
        self.contract = self._contract(contract)
        self.min_length = min_length
        self.max_length = max_length
    
    def check(self, value):
        if not isinstance(value, list):
            self._failure("value is not list")
        errors = []
        if len(value) < self.min_length:
            errors.append(ContractValidationError(
                "list length is less than %s" % self.min_length))
        if self.max_length is not None and len(value) > self.max_length:
            errors.append(ContractValidationError(
                "list length is greater than %s" % self.max_length))
        for index, item in enumerate(value):
            try:
                self.contract.check(item)
            except ContractValidationError as err:
                name = "%i.%s" % (index, err.name) if err.name else str(index)
                errors.append(ContractValidationError(err.msg, name))

        if errors:
            raise ContractValidationError("can't validate", errors=errors)
    
    def __repr__(self):
        r = "<ListC("
        options = []
        if self.min_length:
            options.append("min_length=%s" % self.min_length)
        if self.max_length:
            options.append("max_length=%s" % self.max_length)
        r += ", ".join(options)
        if options:
            r += " | "
        r += repr(self.contract)
        r += ")>"
        return r


class DictC(Contract):
    
    """
    >>> contract = DictC(foo=IntC, bar=StringC)
    >>> contract.check({"foo": 1, "bar": "spam"})
    >>> contract.check({"foo": 1, "bar": 2})
    Traceback (most recent call last):
    ...
    ContractValidationError: can't validate: ['bar: value is not string']
    >>> contract.check({"foo": 1})
    Traceback (most recent call last):
    ...
    ContractValidationError: can't validate: ['bar is required']
    >>> contract.check({"foo": 1, "bar": "spam", "eggs": None})
    Traceback (most recent call last):
    ...
    ContractValidationError: can't validate: ['eggs is not allowed']
    >>> contract.allow_extra("eggs")
    <DictC(extras=(eggs) | bar=<StringC>, foo=<IntC>)>
    >>> contract.check({"foo": 1, "bar": "spam", "eggs": None})
    >>> contract.check({"foo": 1, "bar": "spam"})
    >>> contract.check({"foo": 1, "bar": "spam", "ham": 100})
    Traceback (most recent call last):
    ...
    ContractValidationError: can't validate: ['ham is not allowed']
    >>> contract.allow_extra("*")
    <DictC(any, extras=(eggs) | bar=<StringC>, foo=<IntC>)>
    >>> contract.check({"foo": 1, "bar": "spam", "ham": 100})
    >>> contract.check({"foo": 1, "bar": "spam", "ham": 100, "baz": None})
    >>> contract.check({"foo": 1, "ham": 100, "baz": None})
    Traceback (most recent call last):
    ...
    ContractValidationError: can't validate: ['bar is required']
    >>> contract.allow_optionals("bar")
    <DictC(any, extras=(eggs), optionals=(bar) | bar=<StringC>, foo=<IntC>)>
    >>> contract.check({"foo": 1, "ham": 100, "baz": None})
    >>> contract.check({"bar": 1, "ham": 100, "baz": None})
    ...     # doctest: +NORMALIZE_WHITESPACE
    Traceback (most recent call last):
    ...
    ContractValidationError: can't validate: 
        ['foo is required', 
         'bar: value is not string']
    >>> contract.check({"foo": 1, "bar": 1, "ham": 100, "baz": None})
    Traceback (most recent call last):
    ...
    ContractValidationError: can't validate: ['bar: value is not string']
    """
    
    def __init__(self, **contracts):
        self.optionals = []
        self.extras = []
        self.allow_any = False
        self.contracts = {}
        for key, contract in contracts.items():
            self.contracts[key] = self._contract(contract)
    
    def allow_extra(self, *names):
        for name in names:
            if name == "*":
                self.allow_any = True
            else:
                self.extras.append(name)
        return self
    
    def allow_optionals(self, *names):
        for name in names:
            if name == "*":
                self.optionals = self.contracts.keys()
            else:
                self.optionals.append(name)
        return self
    
    def check(self, value):
        if not isinstance(value, dict):
            self._failure("value is not dict")
        presence_errors = self.check_presence(value)
        item_errors = [x for y in map(self.check_item,value.items()) for x in y]
        if presence_errors or item_errors:
            raise ContractValidationError(
                    "can't validate", 
                    errors=presence_errors + item_errors)
    
    def check_presence(self, value):
        errors = []
        for key in self.contracts:
            if key not in self.optionals and key not in value:
                errors.append(ContractValidationError("%s is required" % key))
        return errors
    
    def check_item(self, item):
        errors = []

        key, value = item
        if key in self.contracts:
            try:
                self.contracts[key].check(value)
            except ContractValidationError as err:
                name = "%s.%s" % (key, err.name) if err.name else key
                errors.append(ContractValidationError(err.msg, name))
        elif not self.allow_any and key not in self.extras:
            errors.append(ContractValidationError("%s is not allowed" % key))

        return errors
    
    def __repr__(self):
        r = "<DictC("
        options = []
        if self.allow_any:
            options.append("any")
        if self.extras:
            options.append("extras=(%s)" % (", ".join(self.extras)))
        if self.optionals:
            options.append("optionals=(%s)" % (", ".join(self.optionals)))
        r += ", ".join(options)
        if options:
            r += " | "
        options = []
        for key in sorted(self.contracts.keys()):
            options.append("%s=%r" % (key, self.contracts[key]))
        r += ", ".join(options)
        r += ")>"
        return r


class EnumC(Contract):
    
    """
    >>> contract = EnumC("foo", "bar", 1)
    >>> contract
    <EnumC('foo', 'bar', 1)>
    >>> contract.check("foo")
    >>> contract.check(1)
    >>> contract.check(2)
    Traceback (most recent call last):
    ...
    ContractValidationError: value doesn't match any variant
    """
    
    def __init__(self, *variants):
        self.variants = variants[:]
    
    def check(self, value):
        if value not in self.variants:
            self._failure("value doesn't match any variant")
    
    def __repr__(self):
        return "<EnumC(%s)>" % (", ".join(map(repr, self.variants)))


class CallableC(Contract):
    
    """
    >>> CallableC().check(lambda: 1)
    >>> CallableC().check(1)
    Traceback (most recent call last):
    ...
    ContractValidationError: value is not callable
    """
    
    def check(self, value):
        if not callable(value):
            self._failure("value is not callable")
    
    def __repr__(self):
        return "<CallableC>"


class CallC(Contract):
    
    """
    >>> def validator(value):
    ...     if value != "foo":
    ...         return "I want only foo!"
    ...
    >>> contract = CallC(validator)
    >>> contract
    <CallC(validator)>
    >>> contract.check("foo")
    >>> contract.check("bar")
    Traceback (most recent call last):
    ...
    ContractValidationError: I want only foo!
    """
    
    def __init__(self, fn):
        if not callable(fn):
            raise RuntimeError("CallC argument should be callable")
        argspec = inspect.getargspec(fn)
        if len(argspec.args) - len(argspec.defaults or []) > 1:
            raise RuntimeError("CallC argument should be"
                               " one argument function")
        self.fn = fn
    
    def check(self, value):
        error = self.fn(value)
        if error is not None:
            self._failure(error)
    
    def __repr__(self):
        return "<CallC(%s)>" % self.fn.__name__


class ForwardC(Contract):
    
    """
    >>> nodeC = ForwardC()
    >>> nodeC << DictC(name=StringC, children=ListC[nodeC])
    >>> nodeC
    <ForwardC(<DictC(children=<ListC(<recur>)>, name=<StringC>)>)>
    >>> nodeC.check({"name": "foo", "children": []})
    >>> nodeC.check({"name": "foo", "children": [1]})
    Traceback (most recent call last):
    ...
    ContractValidationError: can't validate: ["children: can't validate"]
    >>> nodeC.check({"name": "foo", "children": [ \
                        {"name": "bar", "children": []} \
                     ]})
    """
    
    def __init__(self):
        self.contract = None
        self._recur_repr = False
    
    def __lshift__(self, contract):
        if self.contract:
            raise RuntimeError("contract for ForwardC is already specified")
        self.contract = self._contract(contract)
    
    def check(self, value):
        self.contract.check(value)
    
    def __repr__(self):
        # XXX not threadsafe
        if self._recur_repr:
            return "<recur>"
        self._recur_repr = True
        r = "<ForwardC(%r)>" % self.contract
        self._recur_repr = False
        return r


class GuardValidationError(TypeError):
    
    """
    Raised when guarded function gets invalid arguments,
    inherits error message from corresponding ContractValidationError
    """
    
    pass


def guard(**kwargs):
    """
    Decorator for protecting function with contracts
    
    >>> @guard(a=StringC)
    ... def fn(a, b, c=None):
    ...     return (a, b, c)
    ...
    >>> fn("foo", "bar")
    ('foo', 'bar', None)
    >>> fn(1, "bar")
    Traceback (most recent call last):
    ...
    GuardValidationError: value is not string
    >>> @guard(c=IntC)
    ... def fn(a, b, c=None):
    ...    return (a, b, c)
    ...
    >>> fn(1, 2)
    (1, 2, None)
    >>> fn(1, 2, "foo")
    Traceback (most recent call last):
    ...
    GuardValidationError: value is not int
    """
    contracts = {}
    for name, contract in kwargs.items():
        contracts[name] = contract if isinstance(contract, Contract) \
                                   else contract()
    def wrapper(fn):
        argspec = inspect.getargspec(fn)
        @functools.wraps(fn)
        def decor(*args, **kwargs):
            try:
                for argname, value in zip(argspec.args, args) + kwargs.items():
                    if argname in contracts:
                        contracts[argname].check(value)
            except ContractValidationError as (errno, ):
                raise GuardValidationError(errno)
            return fn(*args, **kwargs)
        guards = []
        for name, contract in contracts.items():
            guards.append("%s=%r" % (name, contract))
        decor.__doc__ = "guarded with %s\n\n" % (", ".join(guards)) + \
                        (decor.__doc__ or "")
        return decor
    return wrapper
