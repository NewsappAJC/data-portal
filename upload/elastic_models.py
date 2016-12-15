from elasticsearch_dsl import DoctType, Text, Keyword, Nested, Date
from elasticsearch_dsl.connections import connections

# Define a default ElasticSearch client
connections.create_connection(hosts=['localhost'])

class Table(DocType):
    user = Text(analyzer='snowball', fields={'raw': String(index='not_analyzed')})
    topic = Text()
    name = Text(analyzer='snowball')

    def save(self, **kwargs):
        return super(Table, self).save(**kwargs)

class Column(DocType):
    name = Text(analyzer='snowball')
    mysql_type = Text(analyzer='snowball')
    ajc_type = Text(analyzer='snowball')

    def save(self, **kwargs):
        return super(Table, self).save(**kwargs)

    class Meta:
        index = 'column'

