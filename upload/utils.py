# Python standard lib imports
import re
import pdb # for debugging

# Third party imports
from csvkit import sql, table

#remove quote chars csvkit puts around capitalized column names, change engine to MYISAM
#if routine errors occur, use this to modify the create table statement
#deprecate when we start interactively handling field types
def polish_create_table(create_table):
    create_table=create_table.replace('"','')
    
    create_table=create_table.replace(");",")ENGINE=MYISAM;")
    
    return create_table

#--------------------------------------------
# Infer datatypes of the columns in a csv and
# return tuples with column names and types
#--------------------------------------------
def get_column_types(filepath):
    # Load the csv and use csvkit's sql.make_table utility 
    # to infer the datatypes of the columns
    f = open(filepath,'r')
    csv_table = table.Table.from_csv(f,name='mytable')
    sql_table = sql.make_table(csv_table)
    headers = []

    for column in sql_table.columns:
        raw_type = str(column.type)

        # Use regex to check if there's a length argument. If so, remove it
        # from the type name, and get if from the column.type property
        clean_type = re.sub(r'\(\w+\)', '', raw_type)
        try:
            length = column.type.length
        except AttributeError:
            length = None

        headers.append({
            'name': column.name, 
            'datatype': clean_type,
            'length': length
        })

    pdb.set_trace()

    return headers
