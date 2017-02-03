# Stdlib imports
import os

# Third-party imports
from sqlalchemy import create_engine

# Constants
DATA_WAREHOUSE_URL = os.environ.get('DATA_WAREHOUSE_URL')

# Takes a name_query string and returns a list of dicts
# containing database information, columns searched and a SQLalchemy query result
def table_search(query, table, search_columns, preview):
    sql_query = '''
        select * from imports.{table}
        where MATCH('{search_columns}')
        AGAINST("{query}" IN BOOLEAN MODE)
        '''.format(table=table, search_columns=search_columns, query=query)
    
    if preview:
        sql_query+='LIMIT 5'

    connection = connect_to_db()
    search_result = connection.execute(sql_query).fetchall()
    connection.close()

    if len(search_result)>0:
        result = { 'table' : table,
                   'search_columns' : search_columns}
        result['preview']={}
        result['preview']['headers'] = search_result[0].keys()            

        values = []
        for row in search_result:
            values.append(row.values())            
        result['preview']['data'] = values
    
    return result

def warehouse_search(query):
    if len(query)>0:
        connection = connect_to_db()

        #SQL statement below pulls unique database-table-columns combos
        #to feed into a search
        tables_to_search = connection.execute(
            '''SELECT t.database, t.table,
            CONCAT('`',
                GROUP_CONCAT(c.column SEPARATOR '`,`'),'`'
                ) AS search_columns
            FROM data_import_tool.upload_table t
            JOIN data_import_tool.upload_column c
            ON t.id=c.table_id
            WHERE RIGHT(c.information_type,4) = 'name'
            GROUP BY 1,2''').fetchall()

        connection.close()
        
        results = []
        for table in tables_to_search:
            result = table_search(query,connection,table['database'],
                                  table['table'],table['search_columns'],True)        

            if result:
                results.append(result)

        return results

def connect_to_db():
    engine = create_engine(DATA_WAREHOUSE_URL)
    return engine.connect()

