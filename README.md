# thor-perusal
\- a stupid name for an Appengine search API wrapper.

thor-perusal is a wrapper for Google Appengine's search API that uses Django-like syntax for searching and filtering documents in search indexes, and this, is it's incredibly condescending readme.

## Getting Started: An Example
... and a comparison.

### Setting up thor-perusal

Setting up thor-perusal is simple. Clone the repo into a folder in your project and make sure it's on your PATH. (Yes, it's not a typical Python package, but I can't see what could be simpler than this.)

### The Film Model

Let's say we have some data model based on information about a film. The db model (using Google's `ext.db` API) may look something like:

```python
from google.appengine.ext import db

class Film(db.Model):
    title = db.StringProperty()
    description = db.TextProperty()
    rating = db.FloatProperty()
    released = db.DateField()
```

Simple. A film has a short-string title, a longer text description, a float value for a rating, and a release date. We can store film objects in the datastore and everything's all good. But what happens when we want to search them?

The short answer to the above is, we can't search them. For that, we need Google's search API.

### Searching Films: `google.appengine.api.search`

The search API acts on indexes and documents. Documents are populated with searchable data and then added to indexes, which are then searchable.

With Google's search API module, you might index the document like this:

```python
>>> from google.appengine.api import search
>>> from myapp.models import Film
>>>
>>> # Get or create the films index
>>> i = search.Index(name='films')
>>> # Get the film we want to index
>>> f = Film.get_by_key_name('die-hard')
>>> print f.title, f.description, f.rating, f.released
'Die Hard' 'Bloody awesome' 10.0 datetime.date(1989, 02, 03)
>>>
>>> # Construct the fields that will make up our document
>>> fields = [
...     search.TextField(name='title', value=f.title),
...     search.TextField(name='description', value=f.description),
...     search.NumberField(name='rating', value=f.rating),
...     search.DateField(name='released', value=f.released)
... ]
>>> # Create the document object using the film's datastore key name as
>>> # the document ID
>>> doc = search.Document(doc_id=f.key().name(), fields=fields)
>>> # Add the document to the films index
>>> i.add(doc)
```

Now the document describing _Die Hard_ has been indexed, let's search the index for it:

```python
>>> results = i.search(search.Query('die'))
>>> for d in results:
...     print d
...
<search.ScoredDocument object ...>
```

Just as expected, there it is: our document describing _Die Hard_. Now let's try and print the film title:

```python
>>> # A document has a list of fields matching the list of fields you passed in
>>> # when instantiating the document
>>> for field in d.fields:
...     if field.name == 'title':
...         print field.value
...
'Die Hard'
```

Look at how much work we have to do to get the film's title. This is because a `ScoredDocument` object stores its content in a list of field objects and seemingly provides no way of directly accessing their content via the document instance.

### Searching Films: thor-perusal

Let's see how (hopefully) thor-perusal makes the indexing and searching process simpler.

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

Notice that this is basically a duplication of the definition for the `Film` datastore model. People constantly refer to the DRY (Don't Repeat Yourself) principle, yet they also constantly refer to the 'be explicit' principal. In this case, you can't do both, so thor-perusal prefers explicit definition of document classes. Just because the two definitions happen to be the same doesn't mean they have anything to do with each other.

To index a film document, instantiate and populate it with data, and then add it to thor-perusal's provided `Index` class:

```python
>>> from google.appengine.ext import db
>>> from search import indexes
>>> from myapp.models import Film
>>> from myapp.documents import FilmDocument
>>>
>>> # Note that this Index class has a similar interface to,
>>> # but is not, Google's Index class
>>> i = indexes.Index(name='films')
>>> f = Film.get_by_key_name('die-hard')
>>> # DocumentModel objects can be instantiated with keyword args matching
>>> # field names defined on the class. **db.to_dict(f) is just a shortcut
>>> # to instantiating a FilmDocument with the field values on the Film
>>> # object, since the two share the same field names
>>> doc = FilmDocument(doc_id=f.key().id(), **db.to_dict(f))
>>> i.add(doc)
```

Now to get at the document, as before, search the index, but this time, the results returned from the search are instances of your FilmDocument class, meaning that the field data is accessible through the field names as attributes on the object, as you'd expect:

```python
>>> # You need to pass the document class (FilmDocument here) to the
>>> # index's search method so that it knows what class to instantiate
>>> # with the search results
>>> results = i.search(FilmDocument).keywords('die hard awesome')
>>> for d in results:
...     print d.title, d.description, d.rating, d.released
...
'Die Hard', 'Bloody awesome', 10.0, datetime.date(1989, 02, 03)
```

From a basic standpoint, that's all there is to it. There is various filtering and ordering that can be applied to search queries, refer to the reference for the [`Index`](#index) class for more in-depth example queries.



## Reference

### DocumentModel

A `DocumentModel` allows you to define the names and types of [fields](#fields) for your document. Reusing the film example from above:

```python
class FilmDocument(DocumentModel):
    title = fields.TextField(default='Untitled')
    description = fields.TextField()
    rating = fields.FloatField(minimum=0, maximum=10.0, default=0)
    released = fields.DateField()
```

As you can see this time we've declared certain fields with extra keyword arguments. See [fields](#fields) for more info on specific options for each field.

Instantiating a `DocumentModel` subclass with keyword arguments matching the defined fields automatically sets those fields with the given values, and initialises any other fields with any defaults they were initially declared with, with the `default` keyword argument.

```python
>>> fd = FilmDocument(title='Dirty Harry', description='Stars Clint Eastwood with epic sideburns.')
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
