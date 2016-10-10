# Jeff just put the functions here and we can import them in
# tasks.py 

#remove quote chars csvkit puts around capitalized column names, change engine to MYISAM
#if routine errors occur, use this to modify the create table statement
#deprecate when we start interactively handling field types
def polish_create_table(create_table):
    create_table=create_table.replace('"','')
    
    create_table=create_table.replace(");",")ENGINE=MYISAM;")
    
    return create_table