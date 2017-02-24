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

Environment configuration
---

This tool needs access to a Django database where it can store metadata about each upload, the MySQL server where you want the uploaded data to live, Amazon S3, and a Redis datastore. I know that's a lot, but I've tried to make configuration as painless as possible. To configure your local setup, copy `config/secrets.cfg.example` to `config/secrets.cfg`, and enter your credentials for __every__ field.

Create a user
---
You can create a user by running `$ ./manage.py createsuperuser` from the root of the project and following the prompts.

Development
---
Because there are a lot of moving parts, starting the dev server is a little more involved than in the average project. In short: you need to start the Redis server, start the Celery process, and then run the regular Django development server.

* Start redis server: `$ redis-server`

* Start celery process in debug mode: `$ celery worker --app=data_import_tool --loglevel=debug`

* Start dev server: `$ ./manage.py runserver_plus`

Static assets live in the `static` dir of the project root, and are compiled to the `staticfiles` dir. Within each app, asynchronous tasks live in `tasks`, and helper functions can be found in `utils.py`. For more information about the layout of the app, see Django's excellent documentation at [www.djangoproject.com](https://www.djangoproject.com/).

Run tests
---
If you want to add tests, add them in a `tests.py` file in the app you want to test, and they'll be automatically picked up by the Django testing framework. It might take a couple minutes for the tests to run.

`python manage.py test`
