# thor-perusal
\- a stupid name for an Appengine search API wrapper.

Thor Perusal is a wrapper for Google Appengine's search API that uses Django-like syntax for searching and filtering search indexes.

Why not just write a haystack backend? Because it was quicker to write this than to learn how to write something to plug into something that someone else has defined. Plus, it seems unnecessarily tied to Django, whereas this is only tied to Appengine.

## Documents and Indexes

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

An instance of this document can then be indexed using the provided `Index` class (this time from `search.indexes` and not Google's API):

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
