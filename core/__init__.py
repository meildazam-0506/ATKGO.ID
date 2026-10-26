DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'db_storethesis',
        'USER': 'root',
        'PASSWORD': 'rootpassword',
        'HOST': '127.0.0.1',
        'PORT': '3309',
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    }
}


import pymysql

pymysql.install_as_MySQLdb()
