Data Import Tool
=====

A Django app that creates a standard interface for data reporters to upload files to a shared MySQL database and Amazon S3. Saves metadata about each table uploaded to the database to make searching easier.

The app prompts the user to upload a .csv file and add useful information about it, such as the topic and the source. It then uploads the .csv file to an S3 bucket, and prompts the user to categorize each of the columns in the table.

The app uses Celery to spawn a separate worker process to ensure that the request doesn't time out. It then uses the csvkit library to infer the type of each column and generate a MySQL table schema. It uses these datatypes to generate a CREATE TABLE query and then executes a LOAD DATA INFILE statement to write the csv to a database of the user's choosing within the AJC datastore. 

This tool is configured for easy deployment on Heroku.

Installation
---
* Install python dependencies

```
$ pip install -r requirements.txt
```

*ENVIRONMENTAL VARIABLES*
This tool needs access to a Django database where it can store metadata about each upload, the MySQL server where you want the uploaded data to live, Amazon S3, and a Redis datastore. To establish these connections it's necessary to set a few environmental variables. All the necessary variables are listed below - I recommend using virtualenvwrapper and exporting these environmental variables in the `postactivate` shell script. 

* DATABASE_URL 
  
  Format: `mysql://USER:PASSWORD@HOST:PORT/NAME`

  Purpose: The address of the MySQL server where Django will store metadata about each upload.

* DATA_WAREHOUSE_URL 

  Format: `mysql://USER:PASSWORD@HOST:PORT/NAME`

  Purpose: The server where you want uploaded files to live. Be sure you have the correct permissions and that the MySQL server is set to accept LOAD DATA INFILE statements. For safety, this account should have permissions restricted to "CREATE."

* REDIS_URL

  Format: Varies. If you're using Heroku's Redis add-on, get the url by running `heroku config | grep REDIS`

  Purpose: The Redis datastore is a broker that handles messages to and from the Celery worker process.

* S3_BUCKET

  Format: `ajc-news-apps`

  Purpose: The bucket where the original datafiles will live.

* AWS_ACCESS_KEY, AWS_SECRET_KEY

  Format: Your access key and secret key for the AWS bucket that will be updated by the app.

Run dev server
---
```
$ python manage.py runserver_plus
```

