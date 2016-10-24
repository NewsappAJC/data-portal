# Python standard lib imports
import re
import pdb # for debugging only
from collections import defaultdict

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
# return a list of dicts with the columns names,
# length, and type
#--------------------------------------------
def get_column_types(filepath):
    # Load the csv and use csvkit's sql.make_table utility 
    # to infer the datatypes of the columns.
    f = open(filepath,'r')
    csv_table = table.Table.from_csv(f)
    sql_table = sql.make_table(csv_table)

    headers = [] # Will hold information about all of our column headings
    preexisting = [] # Will keep track of duplicate column names

    for column in sql_table.columns:

        # Clean the type and name values
        raw_type = str(column.type)
        clean_type = re.sub(r'\(\w+\)', '', raw_type)
        
        # Temporary fix for issue #19
        if raw_type == 'BOOLEAN':
            raw_type = 'VARCHAR(10)'

        # Append a number to a column if that column name already exists in the table
        clean_name = str(column.name)
        if clean_name in preexisting:
            preexisting.append(clean_name)
            c = preexisting.count(clean_name) - 1
            clean_name += str(c)

        # Remove spaces at the beginning of the string, replace spaces and
        # underscores with hyphens, strip all non-alphanumeric characters
        rs = [(r'^ |^-|^_', ''), (r' |-', '_'), (r'[^_0-9a-zA-Z]+', '')]
        for r, sub_ in rs:
            clean_name = re.sub(r, sub_, clean_name)
        clean_name = clean_name.lower()[:60] # MySQL allows 64 character column names max

        try:
            length = column.type.length
        except AttributeError:
            length = ''
        headers.append({
            'name': clean_name, 
            'datatype': clean_type,
            'raw_type': raw_type,
            'length': length,
            'sample_data': []
        })

    # Give the user sample data to help them categorize the different columns
    data = csv_table.to_rows()

    for row in data[:3]:
        for i in range(len(row)):
            ex = str(row[i])
            headers[i]['sample_data'].append(ex)

    for h in headers:
        h['sample_data'] = (', ').join(h['sample_data']) + ' ...'

    return headers

#--------------------------------------------
# Write the original CSV to s3. The s3 task will
# load the data from s3
#--------------------------------------------
def write_originals_to_s3():
    # Access S3 bucket using credentials in ~/.aws/credentials
    session = boto3.Session(profile_name='data_warehouse')
    s3 = session.resource('s3')
    bucket = s3.Bucket(BUCKET_NAME)

    # Check if a file with the same name already exists in the
    # S3 bucket, and if so throw an error
    try:
        bucket.download_file(table_name, '/tmp/s3_test_file')
        messages.add_message(request, messages.ERROR, 'A file with that name already exists in s3')
        return render(request, 'upload.html', {'form': form})
    except botocore.exceptions.ClientError:
        pass

    # Write the file to Amazon S3
    bucket.put_object(Key='{db_name}/{today}-{table}/original/{filename}.csv'.format(
        db_name = db_name, 
        today = date.today().isoformat(),
        table = table_name,
        filename = table_name), Body=fcontent)

    # Generate a README file
    readme_template = open(os.path.join(settings.BASE_DIR, 'readme_template'), 'r').read()
    readme = readme_template.format(topic=topic.upper(), 
            div='=' * len(topic),
            reporter=reporter_name, 
            aq=next_aquisition, 
            owner=owner, 
            contact=press_contact,
            number=press_contact_number,
            email=press_contact_email)

    # Write the README to the S3 bucket
    bucket.put_object(Key='{db_name}/{today}-{table}/README.txt'.format(
        db_name = db_name, 
        today = date.today().isoformat(),
        table = table_name), Body=readme)

    logging.info('File written to S3 bucket')
    return
