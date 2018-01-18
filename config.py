#!/usr/bin/python
# -*- coding: UTF-8 -*-
import os
basedir=os.path.abspath(os.path.dirname(__file__))

class Config():
    SECRET_KEY=os.environ.get("SECRET_KEY") or "hard_to_guess_string"

    @staticmethod
    def init_app(app):
        pass

class DevConfig(Config):
    DEBUG=False
    SQLALCHEMY_DATABASE_URI='mysql+pymysql://root:zx1994617@127.0.0.1:3306/testsql?charset=utf8'
    SQLALCHEMY_TRACK_MODIFICATIONS=True
    MONGODB_SETTINGS = {'db':'Datatable','alias':'default'}
    # MONGODB_SETTINGS = {'db':'Datatable','host': '192.168.98.133', 'port': 27017}
    JOBS = [
        {
            'id': 'createschuler_job',
            'func': 'app.main.mongo_service:test',
            'args': None,
            'trigger': 'interval',
            'seconds': 60
        }
    ]

config={
    "dev":DevConfig
}



