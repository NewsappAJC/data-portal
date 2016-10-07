from __future__ import absolute_import

from celery import shared_task

@shared_task
def load_infile(x,y):
    # Create a connection to the data warehouse 
    engine = sqlalchemy.create_engine(URL + '?local_infile=1')
    connection = engine.connect()

    # Check if a database with the given name exists. If it doesn't, create one.
    connection.execute('CREATE DATABASE IF NOT EXISTS {}'.format(db_name))
    connection.execute('USE {}'.format(db_name))
    logging.info('Using database {}'.format(db_name))

    # Use csvkit to generate a CREATE TABLE statement based on the data types
    # in the csv
    create_table_q = subprocess.check_output(['csvsql', path])
    query = r"""
        {create_table}
        LOAD DATA LOCAL INFILE "{path}" INTO TABLE {db}.{table}
        FIELDS TERMINATED BY "{delimiter}" LINES TERMINATED BY "\n"
        IGNORE 1 LINES;
        """.format(create_table=create_table_q,
                path=path,
                db=db_name,
                table=table_name,
                delimiter=delimiter)

    # Create the table and load in the data
    connection.execute(query)

    # Return a preview of the top few rows in the table
    # to check if the casting is correct. Save data to session
    # so that it can be accessed by other views
    data = connection.execute('SELECT * FROM {}'.format(table_name))
    headers = data.keys()

