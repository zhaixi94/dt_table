#!/usr/bin/python
# -*- coding: UTF-8 -*-
from . import db,login_manager,mdb
from werkzeug.security import generate_password_hash,check_password_hash
from flask_login import UserMixin


class Permission:
    FOLLOW = 0x01
    COMMENT = 0x02
    WRITE_ARTICLES = 0x04
    MODERATE_COMMENTS = 0x08
    ADMINISTER = 0x80


class Role(db.Model):
    __tablename__='roles'
    id=db.Column(db.Integer(),primary_key=True)
    name=db.Column(db.String(64),unique=True)
    default=db.Column(db.Boolean,default=False,index=True)
    permissions=db.Column(db.Integer)
    users = db.relationship("User", backref='role',lazy='dynamic')

    @staticmethod
    def insert_roles():
        roles={
            'User':(Permission.FOLLOW|Permission.COMMENT|Permission.WRITE_ARTICLES,True),
            'Moderator':(Permission.FOLLOW|Permission.COMMENT|Permission.WRITE_ARTICLES|
                         Permission.MODERATE_COMMENTS,False),
            'Administrator':(0xff,False)}
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role=Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles [r][1]
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return "<Role %s>"%self.name

class User(UserMixin,db.Model):
    __tablename__='users'
    id=db.Column(db.Integer(),primary_key=True)
    email=db.Column(db.String(64),unique=True,index=True)
    username=db.Column(db.String(64),unique=True)
    password_hash = db.Column(db.String(128))
    role_id = db.Column(db.Integer(), db.ForeignKey("roles.id"))

    # def __init__(self,**kwargs):
    #     super(User,self).__init__(**kwargs)
    #     if self.role is None:
    #         if self.email == current_app.config["FLASKY_ADMIN"]:
    #             self.role = Role.query.filter_by(permission=0xff).first()
    #         if self.email is None:
    #             self.role = Role.query.filter_by(default=True).first()

    @property
    def password(self):
        raise AttributeError("password is not a readable attribute")

    @password.setter
    def password(self,password):
        self.password_hash=generate_password_hash(password=password)
    def verify_password(self,password):
        return check_password_hash(self.password_hash,password=password)

#合同表

class Case(mdb.Document):
    create_time = mdb.DateTimeField()
    case_id=mdb.StringField()
    customer_id = mdb.IntField()
    customer_name = mdb.StringField()
    ic_number = mdb.StringField()
    is_renew_case = mdb.IntField()
    amount = mdb.DecimalField()
    start_date = mdb.DateTimeField()
    end_date = mdb.DateTimeField()
    pay_date = mdb.DateTimeField()
    case_tenor = mdb.IntField()
    #case_times = mdb.IntField() 签约次数，不一定需要
    sale_name = mdb.StringField()
    risk_manager_name = mdb.StringField()
    approver = mdb.StringField()
    approve_time = mdb.DateTimeField()
    approve_status = mdb.StringField()
    card_name = mdb.StringField()
    shop_id = mdb.IntField()
    plateform_fee=mdb.DecimalField()
    guarantor_fee=mdb.DecimalField()
    service_fee1 = mdb.DecimalField()
    service_fee2 = mdb.DecimalField()
    risk_fee = mdb.DecimalField()
    payment_date = mdb.DateTimeField()#本期应还时间
    case_status = mdb.ListField()  # [初审,复审,放款,还款,代还申请,代还批复,提前还清申请,提前还清批复,到期提醒,电催,外催,结束]
    status_code = mdb.StringField()
    recommend_name = mdb.StringField()
    recommend_fee = mdb.DecimalField()  # 中介费
    logs = mdb.DictField()

    def __repr__(self):
        return '<Case %s>'%self.case_id

#合同日志表
class CaseLogs(mdb.Document):
    date = mdb.DateTimeField()
    date_string = mdb.StringField()  # 时间段
    events_matrix = mdb.ListField()
    events = mdb.ListField()

    def __repr__(self):
        return '<Caselogs %s>' % self.date.strftime('%Y-%m-%d')

class ErrorLogs(mdb.Document):
    date = mdb.DateTimeField()
    error = mdb.StringField()

def __repr__(self):
    return "<User %s>"%self.username

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))