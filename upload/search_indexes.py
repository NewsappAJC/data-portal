import datetime
from haystack import indexes
from .models import Table

# Create a search index that Haystack uses to find matching results
class TableIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)

    def get_model(self):
        return Table

