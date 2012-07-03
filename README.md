# thor-perusal
\- a stupid name for an Appengine search API wrapper.

Thor Perusal is a wrapper for Google Appengine's search API that uses Django-like syntax for searching and filtering search indexes.

Why not just write a haystack backend? Because it was quicker to write this than to learn how to write something to plug into something that someone else has defined. Plus, it seems unnecessarily tied to a database API (Django's ORM) while this is database agnostic (but obviously still tied to Appengine.)

## An Example

... and a comparison.

Let's say we have some data model based on information about a film. The db model (using Google's `ext.db` API) may look something like:

```python
from google.appengine.ext import db

class Film(db.Model):
    title = db.StringProperty()
    description = db.TextProperty()
    rating = db.FloatProperty()
    released = db.DateField()
```

Simple. A film has a short-string title, a longer text description, a float value for a rating, and a release date.

With Google's search API you might index the document something like this:

```python
>>> from google.appengine.api import search
>>> from myapp.models import Film
>>>
>>> i = search.Index(name='films')
>>> f = Film.get_by_key_name('die-hard')
>>> f.title, f.description, f.rating, f.released
'Die Hard', 'Bloody awesome', 10.0, datetime.date(1989, 02, 03)
>>>
>>> fields = [
...     search.TextField(name='title', value=f.title),
...     search.TextField(name='description', value=f.description),
...     search.NumberField(name='rating', value=f.rating),
...     search.DateField(name='released', value=f.released)
... ]
>>> doc = search.Document(doc_id=f.key().name(), fields=fields)
>>> i.add(doc)
```

and then search that index:

```python
>>>
>>> for d in i.search(search.Query('die')):
...     print d
...
<search.Document object ...>
```

And just as expected, there it is: our document describing a film. Let's print the film title:

```python
>>> for field in d.fields:
...     if field.name == 'title':
...         print field.value
...
'Die Hard'
```

You might wonder why we had to do this just to print the title of the film. It's because a document (`ScoredDocument`) object returned from the search API has only a list of its fields, the values of which are not directly accessible from the object.

See how (hopefully) much simpler it becomes with thor-perusal.

First, define the document class to describe the film data:

```python
from search import indexes
from search import fields

class FilmDocument(indexes.DocumentModel):
    title = fields.TextField()
    description = fields.TextField()
    rating = fields.FloatField()
    releaseed = fields.DateField()
```

To index a film document, instantiate and populate it with data, and then add it to the `Index` class provided:

```python
>>> from google.appengine.ext import db
>>> from search import indexes
>>> from myapp.models import Film
>>> from myapp.documents import FilmDocument
>>>
>>> # Note that this is simlar syntax, but a different class to Google's
>>> # Index class
>>> i = indexes.Index(name='films')
>>> f = Film.get_by_key_name('die-hard')
>>> doc = FilmDocument(doc_id='die_hard', **db.to_dict(f))
>>> i.add(doc)
```

Now to get at the document, as before, search the index, but this time, the results returned from the search are instances of your FilmDocument class, meaning that the field data is accessible through the field names as attributes on the object, as you'd expect:

```python
>>> for d in i.search(FilmDocument).keywords('die hard awesome'):
...     print d.title, d.description, d.rating, d.released
...
'Die Hard', 'Bloody awesome', 10.0, datetime.date(1989, 02, 03)
```

That's all there is to it

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

Any values assigned to properties that subclass `fields.Field` on a document object are automatically converted to their equivalent value for the search API:

```python
>>> fd.released = '1971-12-23'
>>> fd.released
datetime.date(1971, 12, 23)
```

All fields take one standard option:

`default`: The default value for this field if no value is assigned to it. TODO: There's weird logic here to do with not knowing how to represent a None value in search, so a default value is always forced, annoyingly

#### TextField

Represents a body of text. Any value assigned to this field will be converted to a text value and then passed through the given indexer, if any, before being indexed.

Options:

* `indexer`: A function that takes a text value and returns a Python list of tokens to index this document against. See (indexers)[#indexers] for ones included by default.

#### IntegerField

Represents an integer value.

Options:

* `maximum`: The maximum value for this field to take
* `minimum`: The minimum value for this field to take

#### FloatField

Represents a floating point value

Options:

see [`IntegerField`](#integerfield)

#### DateField

Represents a Python date object. `datetime.date` objects are supported natively by the search API, however, datetime.datetime objects are not, so there is no `DateTimeField`, and if this field recevies a `datetime.datetime` value, it'll automatically be converted to just the `date()` part.

Options:

None, actually. TODO: implement `auto_now_add` and `auto_now`?
