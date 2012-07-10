# thor-perusal
\- a stupid name for an Appengine search API wrapper.

thor-perusal is a wrapper for Google Appengine's search API that uses Django-like syntax for searching and filtering documents in search indexes, and this, is it's incredibly condescending readme.

## Getting Started: An Example
... and a comparison.

### Setting up thor-perusal

Setting up thor-perusal is simple. Clone the repo into a folder in your project and make sure it's on your PATH. (Yes, it's not a typical Python package, but it might become one soon)

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

Look at how much work you've got to do to get the film's title. This is because a `ScoredDocument` object stores its content in a list of field objects and seemingly provides no way of directly accessing their content via the document instance.

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
    released = fields.DateField()
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

From a basic standpoint, that's all there is to it. There is various filtering and ordering that can be applied to search queries, refer to the reference for the Index class for more in-depth example queries.

## Reference

See [here](https://github.com/potatolondon/search/wiki/Reference) for WIP docs.