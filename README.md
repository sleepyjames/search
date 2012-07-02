# thor-perusal
\- a stupid name for an Appengine search API wrapper.

Thor Perusal is a wrapper for Google Appengine's search API that uses Django-like syntax for searching and filtering search indexes.

Why not just write a haystack backend? Because it was quicker to write this than to learn how to write something to plug into something that someone else has defined. Plus, it seems unnecessarily tied to Django, whereas this is only tied to Appengine.

## Overview

### Google's API

Google's search API is based on the concept of adding documents to indexes and then searching those documents via the index. Documents and indexes are created on the fly like so:

```python
>>> from google.appengine.api import search
>>>
>>> i = search.Index(name='films')
>>> fields = [search.TextField(name='title', value='Die Hard'),
>>>     search.NumberField(name='rating', value=5)]
>>> d = search.Document(doc_id='die-hard', fields=fields)
>>> i.add(d)
>>>
>>> for d in i.search('die'):
...     print d
...
<search.Document object at 0xXXXXXXX>
```

If many indexing operations are happening at different times, it may be tricky to keep track of what indexes have what documents with what fields, etc.

### thor-perusal

To help keep a consistent schema between documents added to the same index (we'll come to global search indexes later on) document types can be declared... declaratively, much like datastore/database models are from `google.appengine.ext.db` or `django.db`. The above film document could be defined as:

```python
from search.indexes import DocumentModel
from search import fields

class FilmDocument(DocumentModel):
    title = fields.TextField()
    rating = fields.FloatField(default=0, minimum=0, maximum=5.0)
```

An instance of this document can then be indexed using the provided [`Index`](#index) class (this time from `search.indexes` and not Google's API):

```python
>>> from search.indexes import Index
>>> from myapp.documents import FilmDocument
>>> i = Index(name='films') # Notice the similar syntax
>>> d = FilmDocument(doc_id='die-hard-2', title='Die Hard 2', rating=4.5)
>>> i.add(d)
>>>
>>> for d in i.search('die'):
...     print d.title, d.rating
...
"Die Hard 2" 4.5
```

This is the basic idea of the wrapper around the search API.

## Reference

### DocumentModel

A `DocumentModel` allows you to define the names and types of [fields](#fields) for your document.

```python
class FilmDocument(DocumentModel):
    title = fields.TextField()
    director = fields.TextField()
    rating = fields.FloatField(default=0)
    released = fields.DateField()
```

Instantiating a `DocumentModel` subclass with keyword arguments matching the defined fields automatically sets those fields with the given values, and initialises any other fields with the defaults they were defined with.

```python
>>> fd = FilmDocument(title='Dirty Harry', director='Don Siegel')
>>> fd.title
"Dirty Harry"
>>> fd.rating
0
```

An optional keyword argument to the `DocumentModel` class is `doc_id`. This property defines the search API's internal ID for the document. It is recommended that this is some guessable value based on the document object, since it needs to be known in order to remove a document from an index.

```python
>>> title = 'Dirty Harry'
>>> fd = FilmDocument(doc_id=slugify(title), title=title, ...)
>>> i = Index(name='films')
>>> i.add(fd)
>>> i.remove(fd.doc_id)
```

TODO: make this a definable field?

Meta-information about document objects is stored in `document._meta`. Currently the only thing it stores is a property called `fields` which is a dictionary of `{field_name: field_object}` for all fields defined on the document. TODO: Is this annoying?

### Fields

Fields are used to define the type and behaviour of properties on `DocumentModel` instances.

Any values assigned to properties which subclass `fields.Field` on a document object are automatically converted to their equivalent value for the search API:

```python
>>> fd.released = '1971-12-23'
>>> fd.released
datetime.date(1971, 12, 23)
```

All fields take one standard option:

`default`
  The default value for this field if no value is assigned to it
  TODO: There's weird logic here to do with not knowing how to represent a None value in search, so a default value is always forced, annoyingly

#### TextField

Represents a body of text. Any value assigned to this field will be converted to a text value and then passed through the given indexer, if any, before being indexed.

Options:

`indexer`
  A function that takes a text value and returns a Python list of tokens to index this document against. See (indexers)[#indexers] for ones included by default.

#### IntegerField

Represents an integer value.

Options:

`maximum`
  The maximum value for this field to take

`minimum`
  The minimum value for this field to take

#### FloatField

Represents a floating point value

Options:

see [`IntegerField`](#integerfield)

#### DateField

Represents a Python date object. `datetime.date` objects are supported natively by the search API, however, datetime.datetime objects are not, so there is no `DateTimeField`, and if this field recevies a `datetime.datetime` value, it'll automatically be converted to just the `date()` part.

Options:

None, actually. TODO: implement `auto_now_add` and `auto_now`?
