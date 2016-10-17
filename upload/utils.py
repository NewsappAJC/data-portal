# Jeff just put the functions here and we can import them in
# tasks.py 

#remove quote chars csvkit puts around capitalized column names, change engine to MYISAM
#if routine errors occur, use this to modify the create table statement
#deprecate when we start interactively handling field types
from csvkit import sql

def polish_create_table(create_table):
    create_table=create_table.replace('"','')
    
    create_table=create_table.replace(");",")ENGINE=MYISAM;")
    
    return create_table

def return_column_types(filepath):
    f = open(filepath,'r')
    csv_table = table.Table.from_csv(f,name='mytable')
    sql_table = sql.make_table(csv_table)
    headers_types_lengths = ()

    for column in sql_table.columns:
        header_type_length = ()        
        header_type_length = header_type_length + (column.name,)        

        if "(" in str(column.type):
            header_type_length = header_type_length + (str(column.type).split('(')[0],)
            header_type_length = header_type_length + (column.type.length,)
        else:
            header_type_length = header_type_length + (str(column.type),)            

        headers_types_lengths = headers_types_lengths + (header_type_length,)

    return headers_types_lengths