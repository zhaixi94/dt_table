#!/usr/bin/python
# -*- coding: UTF-8 -*-
from flask import Blueprint

main=Blueprint('main',__name__)


from . import errors,views,forms,sqlhelper,mongo_service
