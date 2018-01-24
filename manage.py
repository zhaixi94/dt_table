#!/usr/bin/python
# -*- coding: UTF-8 -*-
import os
from app import create_app,db
from app.models import User,Role,Case,CaseLogs
from flask_script import Manager,Shell

app=create_app("dev")
manager=Manager(app)

def make_shell_context():
    return dict(app=app,db=db,User=User,Role=Role,Case=Case,CaseLogs=CaseLogs)

manager.add_command("shell",Shell(make_context=make_shell_context))


if __name__=="__main__":
    manager.run()