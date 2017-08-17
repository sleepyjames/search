# Thor

Thor is a wrapper for Google App Engine's search API that uses Django-like syntax for defining documents, and searching and filtering search indexes.

## Example

### Searching films

Say your app has a database of films that needs to be searched. The first step is to define a document class describing the searchable film data:

```python
from thor import indexes, fields

class FilmDocument(indexes.DocumentModel):
    title = fields.TextField()
    description = fields.TextField()
    rating = fields.FloatField()
    released = fields.DateField()
```

To index a film document, instantiate and populate it with data, and then add it to thor's provided `Index` class. It's more likely the data would come from some other source (datastore, database, etc.) but for this example we hand-craft it:

```python
>>> from datetime import date
>>> from thor import indexes
>>> from myapp.documents import FilmDocument
>>>
>>> # This gets a search index by name or creates it if it doesn't exist
>>> i = indexes.Index(name='films')
>>> # Create a film document representing the film Die Hard
>>> doc = FilmDocument(
...     doc_id='die-hard',
...     title='Die Hard',
...     description='The most awesome film ever',
...     rating=9.7,
...     released=date(1989, 2, 3)
... )
>>> # Add the document to the index. In reality this should be done on
>>> # a taskqueue at a rate around 4 docs/sec.
>>> i.put(doc)
```

Now the document has been indexed and is ready to search:

```python
>>> # You need to pass the document class (FilmDocument here) to the
>>> # index's search method so that it knows what class to instantiate
>>> # with the search results
>>> results = i.search(FilmDocument).keywords('die hard awesome')
>>> for d in results:
...     print d.title, d.description, d.rating, d.released
...
'Die Hard', 'The most awesome film ever', 9.7, datetime.date(1989, 02, 03)
```

From a basic standpoint, that's all there is to it. There is various filtering and ordering that can be applied to search queries, refer to the reference for the Index class for more in-depth example queries.

## Reference

See [here](https://github.com/potatolondon/search/wiki/Reference) for WIP docs.
