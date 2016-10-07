web: gunicorn data_import_tool.wsgi --log-level debug
worker: celery worker --app=data_import_tool --loglevel=debug
