"""
Django settings for data_import_tool project.

Generated by 'django-admin startproject' using Django 1.10.1.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""

# Standard library imports
import sys
import os
import ConfigParser

# Django imports
import dj_database_url

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Parse settings from config file
config_path = os.path.join(BASE_DIR, 'config', 'secrets.cfg')
config = ConfigParser.RawConfigParser()
config.read(config_path)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config.get('django', 'secret_key')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party apps
    'django.contrib.humanize',
    'django_extensions',
    # Local apps
    'upload',
    'search'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'data_import_tool.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'data_import_tool.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases
DATABASES = {}
DATABASES['default'] = dj_database_url.parse(config.get('databases', 'dj_database_url'))
# Use MySQL strict mode to escalate truncation warnings to errors. See
# https://docs.djangoproject.com/en/1.10/ref/databases/#setting-sql-mode
DATABASES['default']['OPTIONS'] = {
    'init_command': 'SET sql_mode="STRICT_TRANS_TABLES"' 
}
DATA_WAREHOUSE_URL = config.get('databases', 'data_warehouse_url')

# Creating a local sqlite DB in memory for testing is a lot faster than 
# using MySQL
if 'test' in sys.argv:
    DATABASES['default'] = {'ENGINE': 'django.db.backends.sqlite3'}

# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'

# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/New_York'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)

# Celery
BROKER_URL = config.get('redis', 'redis_url')
BROKER_POOL_LIMIT = 0  # Prevent Celery from creating too many clients
CELERY_REDIS_MAX_CONNECTIONS = 5
CELERY_RESULT_BACKEND = config.get('redis', 'redis_url')
if 'test' in sys.argv:
    CELERY_ALWAYS_EAGER = True  # Run Celery tasks in the same thread if testing

# AWS
AWS_ACCESS_KEY = config.get('s3', 'aws_access_key')
AWS_SECRET_KEY = config.get('s3', 'aws_secret_key')
S3_BUCKET = config.get('s3', 's3_bucket')

