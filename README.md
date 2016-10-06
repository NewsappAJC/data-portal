Data Import Tool
=====

A Django app that creates a simple, standard interface for data reporters to upload files to a shared MySQL database. Currently supports only .csv files, but future versions will support more file formats.

The app runs a sequence of operations on a .csv file uploaded by the user. First, it uploads the .csv file to an S3 bucket, then it uses csvkit to generate a MySQL table schema. After prompting the user to ensure that csvkit has cast all the columns correctly, it creates a table in a database selected by the user.

The app is configured for deployment on Heroku, so it uses the ClearDB add-on to connect to the database and run the queries.

Installation
---
* Install mysql

```
apt-get install mysql
```

* Install python dependencies

```
$ pip install -r requirements.txt
```

Because this tool needs access to a couple different databases, S3 and a Redis datastore, it's necessary to set a few environmental variables. All the necessary environmental variables are listed below.

* Set the DATABASE_URL environmental variable to a user with access to the MySQL server. Use the following format: `mysql://USER:PASSWORD@HOST:PORT/NAME`. This will be the user account Django uses to update the server.

* Set the DATA_WAREHOUSE_URL environmental variable, using the same format as above. Be sure you have the correct permissions and that the MySQL server is set to accept LOAD DATA INFILE statements. This is the account with permissions restricted to "CREATE" that will add files uploaded by users to the database.

* Set the REDIS_URL environmental variable to the url of your Redis store. If you're using the Redis Heroku addon, you can get that url by running `heroku config | grep REDIS`

* Set S3_BUCKET environmental variable to your Amazon S3 bucket name

* Add a user named `data_warehouse` with access to your S3 bucket to your `.aws/config` file. For instructions on how to create a user in consult the Amazon documentation at [docs.aws.amazon.com](http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html).

Run dev server
---
```
$ python manage.py runserver
```

Wishlist
---
* Add optional categories to each column to make searching easier (shout out to big John Perry's BASIC app that once did pretty much exactly this)
* Along with the interface for uploading data, create an interface that reporters can use to search the databases.

