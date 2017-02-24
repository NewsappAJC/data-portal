Data Portal
=====

This tool is a Django app that creates a standard interface for data reporters to upload files to a shared MySQL database and Amazon S3. It saves metadata about each table uploaded to the database to make searching easier, and provides an interface for viewing and editing metadata about tables.

How it works
---

The app prompts the user to upload a .CSV file and add information about it, such as the topic and the source. It then uploads the file to an S3 bucket, and prompts the user to categorize each of the columns in the table.

The app uses Celery to spawn a separate worker process to ensure that the request doesn't time out while it loads the file into the database. It then uses the csvkit library to infer the type of each column and generate a MySQL table schema (see `upload/tasks.py` for implementation details). It uses these datatypes to generate a CREATE TABLE query and then executes a LOAD DATA INFILE statement to write the csv to a database of the user's choosing within the AJC datastore. 

This tool is configured for deployment on Heroku.

Installation
---
* Install python dependencies

```
$ pip install -r requirements.txt
```

You need to download Redis, which acts as the task broker for the asynchronous processes. You can download redis at [redis.io/download](https://redis.io/download). See the Development section for information about how to run the Redis server.

Environment config
---

This tool needs access to a Django database where it can store metadata about each upload, the MySQL server where you want the uploaded data to live, Amazon S3, and a Redis datastore. I know that's a lot! To establish these connections it's necessary to set a few environmental variables (we're working on doing this via config script instead).

All the many variables you need to set are listed below - I recommend using virtualenvwrapper and exporting these environmental variables in the `postactivate` shell script, so you don't have to manually set them every time you want to run the server locally. See details about how to configure the `postactivate` script at [virtualenvwrapper.readthedocs.io](http://virtualenvwrapper.readthedocs.io/en/latest/scripts.html)

* __DATABASE_URL__: This is the address of the MySQL server where Django will store metadata about each upload.
  
  Format: `mysql://USER:PASSWORD@HOST:PORT/NAME`

* __DATA_WAREHOUSE_URL__: This is the server where you want uploaded files to live. Be sure you have the correct permissions and that the MySQL server is set to accept LOAD DATA INFILE statements. For safety, this account should have permissions restricted to "CREATE."

  Format: `mysql://USER:PASSWORD@HOST:PORT/NAME`

* __REDIS_URL__: This is the Redis datastore is a broker that handles messages to and from the Celery worker process.

  Format: Varies. If you're using Heroku's Redis add-on, get the url by running `$ heroku config | grep REDIS` at the command line

* __S3_BUCKET__: This is the bucket where the original datafiles will live.

  Format: `ajc-data-warehouse`

* __AWS_ACCESS_KEY__, __AWS_SECRET_KEY__: Your access key and secret key for the AWS bucket that will be updated by the app.

* __SECRET_KEY__: The secret key of your Django app. Django automatically generates a SECRET_KEY variable in your_project_name/settings.py - you shouldn't check it into version control, and instead you need to store it as an environmental variable.

Development
---
Because there are a lot of moving parts, starting the dev server is a little more involved than in the average project (I'm working on writing a fabfile to automate this process). To summarize, you need to start the Redis server, start the Celery process, and then run the regular Django development server.

* Start redis server: `$ redis-server`

* Start celery process in debug mode: `$ celery worker --app=data_import_tool --loglevel=debug`

* Start dev server: `$ ./manage.py runserver_plus`

Static assets live in the `static` dir of the project root, and are compiled to the `staticfiles` dir. Within each app, asynchronous tasks live in `tasks`, and helper functions can be found in `utils.py`.

Run tests
---
If you want to add tests, add them in a `tests.py` file in the app you want to test, and they'll be automatically picked up by the Django testing framework. It might take a couple minutes for the tests to run.

`python manage.py test`
