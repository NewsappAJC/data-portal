"""
A collection of utility classes for use elsewhere in the app
"""
# Python standard lib imports
import os
from datetime import date
import re

# Django imports
from django.conf import settings

# Third party imports
import boto3
import botocore

# Constants
BUCKET_NAME = os.environ.get('S3_BUCKET')

class S3Manager(object):
    """
    This module handles creating a connection to S3 and uploading files. It
    provides cool stuff like checking for duplicate filenames and renaming
    files as needed.

    Args:
        local_path (string): The path to the CSV on the user's computer
        table_name (string): The name of the table
    """
    def __init__(self, local_path, table_name):
        key = settings.AWS_ACCESS_KEY
        secret = settings.AWS_SECRET_KEY

        self.client = boto3.client('s3', aws_access_key_id=key,
                                   aws_secret_access_key=secret)
        self.bucket = BUCKET_NAME
        self.local_path = local_path
        self.table_name = table_name

    def _check_duplicates(self, key, i=0):
        """
        Check if a key already exists in S3. If it does, recursively call this
        function. Generate a new key and return it.

        Args:
            key (string): A filename (possibly duplicate of existing filename)
            i (int): A counter that is appended to the end of the filename if
                     a file with that name already exists

        Returns:
            key (string): A non-duplicate filename
        """
        try:
            # Boto3 doesn't have a method to check if a given key already exists.
            # Trying to get metadata and catching the resulting ClientError
            # is the least expensive way to do it
            self.client.head_object(Bucket=self.bucket, Key=key)

            i += 1

            # If there's already a number appended to the end of the key, strip it
            # out so we can append the new number
            r = re.compile(r'\(\d+\)$')
            if r.search(key):
                key = re.sub(r, '', key)

            # Recursive call to check with updated filename suffix
            return self._check_duplicates('{}({})'.format(key, str(i)), i)

        except botocore.exceptions.ClientError:
            return key


    def copy_final_s3(self, tmp_path):
        """
        Copy the original CSV file from the tmp bucket to its permanent home on s3

        Args:
            tmp_path (str): The path to a CSV stored in the temp directory on S3
            table_name (str): The name of the final table
        """
        # Compose a key name
        today = date.today().isoformat()
        stem = '{today}_{table}'.format(table=self.table_name, today=today)

        path = '{stem}/original/{table}.csv'.format(stem=stem,
                                                         table=self.table_name)

        # Check if a directory with the same name already exists in the
        # S3 bucket, and if so change the key.
        unique_path = self._check_duplicates(path)

        # Copy the file to the permanent directory on S3 and delete the
        # temporary file
        self.client.copy(Bucket=self.bucket, CopySource=tmp_path, Key=unique_path)
        self.client.delete_object(Bucket=self.bucket, Key=tmp_path)

        return unique_path

    def write_tempfile_to_s3(self):
        """
        Write a temporary file to the S3 server.

        Args:
            local_path (string): Path to local CSV file
            table_name (string): The name of the table

        Returns:
            s3_path (string): The path to the temporary file on S3
        """
        s3_path = self._check_duplicates('tmp/{}.csv'.format(self.table_name))
        with open(self.local_path, 'r') as f:
            self.client.put_object(Bucket=self.bucket, Key=s3_path, Body=f)

        return s3_path


class TableFormatter(object):
    """
    This module handles formatting column names in a CSV. Initialize it with
    the path to a local .csv file and it will sanitize each of the column
    headers.


    Example usage:
        formatter = TableFormatter('my_local_file.csv')
        column_names = formatter.get_column_names()
    """
    def __init__(self, path):
        self.filepath = path

    def _clean(self, names):
        """
        Parse non-alphanumeric symbols out of table headers, and append a number
        to the end of the column name in the case of duplicates

        Args:
            names (string[]): A list of column names that you want sanitized

        Returns:
            clean_names (string[]): A list of sanitized column names
        """
        preexisting = []  # Will keep track of duplicate column names
        clean_names = []  # Will hold sanitized column names
        for name in names:
            # Append a number to a column name if it already exists in the table
            preexisting.append(name)

            if preexisting.count(name) > 1:
                c = preexisting.count(name) - 1
                name += str(c)

            # Use regex to remove spaces at the beginning of the string, replac
            # spaces and underscores with hyphens, remove line breaks, strip all
            # non-alphanumeric characters
            rxs = [(re.compile(r'-|\s'), '_'), (re.compile(r'\W'), '')]
            clean_name = name

            for rx, sub_ in rxs:
                clean_name = re.sub(rx, sub_, clean_name.strip())

            # MySQL allows 64 character column names maximum
            clean_names.append(clean_name.lower()[:60])

        return clean_names

    def get_column_names(self):
        """
        Get column names and sample data from a CSV without loading the whole
        file into memory

        Returns:
            headers (string[string[]]): A list of sanitized column headers with
            a nested list of sample data
        """
        columns = []
        rows = []
        with open(self.filepath, 'r') as f:
            # Loop through lines to avoid reading the entire file into memory
            for i, line in enumerate(f):
                # Split lines on commas. TODO handle other delimiters
                linef = line.split(',')
                # Generate our list of headers from the first row
                if i == 0:
                    columns = linef
                # Only get sample data from the first 3 rows
                elif i < 4:
                    rows.append(linef)
                # After 4 lines, stop reading the CSV
                else:
                    break

        # Clean the column names to prevent SQL injection
        ccolumns = self._clean(columns)
        headers = []
        i = 0
        for col in ccolumns:
            # Provide default names for unnamed columns
            name = col or str(i)
            if not col:
                i += 1
                name = str(i)
            else:
                name = col
            headers.append({'name': name, 'sample_data': []})

        # Append the sample data to the header objects
        for i in range(len(headers)):
            headers[i]['sample_data'] = [str(x[i]) for x in rows]

        return headers


class Index(object):
    """
    This module handles creation of a query to generate an index for a given
    column in a MySQL table

    Args:
        table_id (string): The UniqueID of a table in the Django DB
        connection (sqlalchemy.engine.connection): A sqlalchemy connection
                                                   object
    """

    def __init__(self, table_id, connection):
        self.table_id = table_id
        self.connection = connection

    def _get_columns(self, data_type):
        query = """
        SELECT CONCAT_WS('.','imports',t,'table') AS table,
            CONCAT('`',GROUP_CONCAT(c.`column` SEPARATOR '`,`'),'`') AS indexes
        FROM data_import_tool.`upload_table` t
        JOIN data_import_tool.`upload_column` c
        ON t.`id`=c.`table_id`
        WHERE RIGHT(c.`information_type`,5) = '{type}'
        AND t.`id`={id}
        GROUP BY 1;
        """.format(id=self.table_id, type=data_type)

        columns = self.connection.execute(query).fetchall()
        return columns

    def create_index(self, data_type):
        """
        Generate the SQL query to create an index, connect to the MySQL,
        database, and create the index

        Args:
            data_type(string): The AJC datatype (eg "name", "address") used
                               to categorize columns
        """
        indexer = self._get_columns(data_type)
        if indexer:
            args = {
                'table': indexer[0]['table'],
                'columns': indexer[0]['indexes']
            }
            query = """
                ALTER TABLE {table} ADD FULLTEXT INDEX `name_index` ({columns})
                """.format(**args)

            self.connection.execute(query)
            return True
        else:
            return False

