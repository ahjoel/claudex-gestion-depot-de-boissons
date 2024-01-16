import os
import dj_database_url


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "01_$0+o6wulo069h2!!%1hrktwc^bkw3ea(^qxd&5u1pr70_4)"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]

# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
   'default': {
      'ENGINE': 'django.db.backends.mysql',
      'NAME': 'claudexb',
      'USER': 'root',
      'PASSWORD': 'root24',
      'HOST': 'localhost',
      'PORT': '3306',
   }
}
