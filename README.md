Data Import Tool
=====

A Django app that creates a simple, standard interface for data reporters to upload files to a shared MySQL database. Currently supports only .csv files, but future versions will support more file formats.

The app runs a sequence of operations on a .csv file uploaded by the user. First, it uploads the .csv file to an S3 bucket, then it uses csvkit to generate a MySQL table schema. After prompting the user to ensure that csvkit has cast all the columns correctly, it creates a table in a database selected by the user.

The app is configured for deployment on Heroku, so it uses the ClearDB add-on to connect to the database and run the queries.

Installation
---
```
$ pip install -r requirements.txt
```
If you haven't already, you will need to download the python MySQL connector from [the Oracle website](http://dev.mysql.com/downloads/connector/python/).

Run dev server
---
```
$ python manage.py runserver
```

Wishlist
---
* Add optional categories to each column to make searching easier (shout out to big John Perry's BASIC app that once did pretty much exactly this)
* Along with the interface for uploading data, create an interface that reporters can use to search the databases.

