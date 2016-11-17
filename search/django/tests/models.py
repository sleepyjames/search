# -*- coding: utf-8 -*-
from django.db import models

from djangae import fields

from ... import (
    fields as search_fields,
    indexers as search_indexers
)

from ..decorators import searchable
from ..documents import Document


class FooDocument(Document):
    name = search_fields.TextField()
    relation = search_fields.TextField()
    is_good = search_fields.BooleanField()
    tags = search_fields.TextField()

    def build(self, instance):
        self.name = instance.name
        self.relation = str(instance.relation_id)
        self.is_good = instance.is_good
        self.tags = "|".join(instance.tags)


class Related(models.Model):
    name = models.CharField(max_length=50)


class FooBase(models.Model):
    class Meta:
        abstract = True

    name = models.CharField(max_length=50)
    relation = models.ForeignKey(Related, null=True)
    is_good = models.BooleanField(default=False)
    tags = fields.ListField(models.CharField)


@searchable(FooDocument)
class Foo(FooBase):
    pass


@searchable()
class FooWithMeta(FooBase):
    class SearchMeta:
        fields = ['name', 'name_lower', 'is_good', 'tags', 'relation']
        field_types = {
            'name': search_fields.TextField,
            'name_lower': search_fields.TextField,
            'relation': search_fields.TextField
        }
        field_mappers = {
            'name_lower': lambda o: o.name.lower(),
            'tags': lambda o: u"|".join(o.tags),
            'relation': lambda o: o.relation.name if o.relation else ''
        }
        corpus = {
            'name': search_indexers.startswith,
            'relation.name': search_indexers.contains
        }
