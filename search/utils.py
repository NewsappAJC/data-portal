
#takes a name_query string and returns a list of dicts
#containing database information, columns searched and a SQLalchemy query result
def warehouse_search(name_query,connection):
    if len(name_query)>0:
        #SQL statement below pulls unique database-table-columns combos to feed into a search
        name_tables_to_search = connection.execute("SELECT CONCAT(t.database,'.',t.table) AS database_table,CONCAT('`',GROUP_CONCAT(c.column SEPARATOR '`,`'),'`') AS search_columns \
                                        FROM data_import_tool.upload_table t \
                                        JOIN data_import_tool.upload_column c \
                                        ON t.id=c.table_id \
                                        WHERE RIGHT(c.information_type,4) = 'name' \
                                        GROUP BY 1").fetchall()

    name_results = []
    for table in name_tables_to_search:
        name_result = {'database_table' : table['database_table'], 'search_columns' : table['search_columns']}
        name_result['matching_records'] = connection.execute('select * from '+ name_result['database_table'] +' where MATCH(' + name_result['search_columns'] +') AGAINST("'+name_query+'" IN BOOLEAN MODE)').fetchall()
        
        if len(name_result['matching_records'])>0:
            name_results.append(name_result)

    return name_results

