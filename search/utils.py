# Stdlib imports
from __future__ import unicode_literals
import os
import csv

# Third-party imports
from sqlalchemy import create_engine

# Local module imports
from upload.utils import S3Manager

# Constants
DATA_WAREHOUSE_URL = os.environ.get('DATA_WAREHOUSE_URL')
TMP_PATH = os.path.join('/tmp', 'ajc-import-searchfile.csv')
BUCKET_NAME = os.environ.get('S3_BUCKET')

# Takes a name_query string and returns a list of dicts
# containing database information, columns searched and a SQLalchemy query result
def table_search(query, table, search_columns, preview):
    # Uncomment the logic below if you want to treat spaces as logical AND
    # r = re.compile(r'(^.)')
    # query = re.sub(r'[^\w\s]', '', query) # Strip out all non-alphanumeric characters
    # query = re.sub(r, '+' + r.match(query).group(1), query)
    # query = re.sub(r'\s', ' +', query) # MySQL treats + as logical AND

    sql_query = '''
        SELECT * FROM imports.{table}
        WHERE MATCH({search_columns})
        AGAINST('{query}' IN BOOLEAN MODE)
        '''.format(table=table, search_columns=search_columns, query=query)

    if preview:
        sql_query+='LIMIT 5'
    else:
        sql_query+='LIMIT 50'

    connection = connect_to_db()
    search_result = connection.execute(sql_query).fetchall()
    connection.close()

    if len(search_result) > 0:
        result = { 'table' : table,
                   'search_columns' : search_columns}
        result['preview']={}
        result['preview']['headers'] = search_result[0].keys()

        values = []
        for row in search_result:
            values.append(row.values())

        result['preview']['data'] = values

        if not preview:
            result['count'] = len(values)

        return (sql_query, result)

    else:
        return None


def get_url(sql_query):
    connection = connect_to_db()
    search_result = connection.execute(sql_query).fetchall()
    connection.close()

    # Add error handling here for cases where the search results array is empty
    with open(TMP_PATH, 'wb') as f:
        fields = search_result[0].keys()
        writer = csv.writer(f, delimiter=',', fieldnames=fields)
        for row in search_result[1:]:
            writer.writeheader()
            writer.write_row(row.values())

    s3 = S3Manager(local_path=TMP_PATH, table_name='ajc-search-results',
                   bucket=BUCKET_NAME)
    unique_key = s3.write_file()
    url = s3.get_presigned_url(unique_key)
    return url


def warehouse_search(query, data_type='name'):
    if len(query)>0:
        connection = connect_to_db()

        #SQL statement below pulls unique database-table-columns combos
        #to feed into a search
        tables_to_search = connection.execute(
            '''SELECT t.table, t.id,
            CONCAT('`',GROUP_CONCAT(c.column SEPARATOR '`,`'),'`') AS search_columns
            FROM data_import_tool.upload_table t
            JOIN data_import_tool.upload_column c
            ON t.id=c.table_id
            WHERE RIGHT(c.information_type,4) = '{}'
            GROUP BY 1'''.format(data_type)).fetchall()

        connection.close()

        results = []
        for table in tables_to_search:
            try:
                query, result = table_search(query, table['table'],
                                             table['search_columns'],True)
                if result:
                    result['id'] = int(table['id'])
                    results.append(result)
            except TypeError:
                continue

        return results

def connect_to_db():
    engine = create_engine(DATA_WAREHOUSE_URL)
    return engine.connect()

