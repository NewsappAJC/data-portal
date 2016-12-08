from haystack import indexes
from .models import Table


class TableIndex(indexes.SearchIndex, indexes.Indexable):
    """Object that handles the flow of data into the search index"""

    # Define the fields we want to store data with
    text = indexes.CharField(document=True, use_template=True)

    # Specify what type of object the search results should return
    def get_model(self):
        return Table

