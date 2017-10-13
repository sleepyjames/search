from django.db import models

class TestModel(models.Model):
    field1 = models.CharField(unique=True, max_length=500)
    field2 = models.TextField()
