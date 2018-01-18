from flask import Flask
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from config import config
from flask_login import LoginManager
from flask_mongoengine import MongoEngine
import pandas as pd
import redis,json,datetime,time
from pandas import DataFrame
from flask_apscheduler import APScheduler


bootstrap=Bootstrap()
moment=Moment()
db=SQLAlchemy()
login_manager=LoginManager()
mdb = MongoEngine()
login_manager.session_protection = 'strong'
login_manager.login_view = 'auth.login'
pool = redis.ConnectionPool(host='127.0.0.1', port=6379, db=0)
red = redis.StrictRedis(connection_pool=pool)
scheduler = APScheduler()

def data_profile():
    from .models import Case, CaseLogs
    from .main.sqlhelper import find_shop

    date_list = CaseLogs.objects().all()
    cases = Case.objects().all()
    print('Loading....')

    log_list = list(event for date in date_list
                    for behave in date.events
                    for event in date.events[behave])
    logs_data = pd.DataFrame(log_list)
    print('Logs Data Complete')

    infolist = list(
        [case.case_id, case.case_status, float(case.amount) if case.amount else 0.0, case.risk_manager_name,case.status_code,case.recommend_name,float(case.recommend_fee) if case.recommend_fee else 0.0,case.is_renew_case,] for case in
        cases)
    case_data = DataFrame(infolist)
    case_data.columns = ['case_id', 'status', 'amount', 'risk_manager_name', 'status_code','recommend_name','recommend_fee','is_renew_case']
    case_data = case_data[~case_data['case_id'].isnull()]
    print('Case Data Complete')


    shop_data = find_shop()  # 查询所有门店的名称
    shop_reflect = {}
    for shop_info in shop_data:
        shop_reflect[int(shop_info['id'])] = shop_info['abbreviation']
    shop_reflect.pop(7)  # 将测试门店除去
    shop=json.dumps(shop_reflect)
    print('Shop Data complete')

    # entire_data = pd.merge(logs_data,case_data,how='left',on='case_id')
    red.set('logs_data', DataFrame(logs_data).to_msgpack(compress='zlib'))
    red.set('case_data', DataFrame(case_data).to_msgpack(compress='zlib'))
    red.set('shop_data', shop)

#定时任务
def clock():
    while True:
        now = datetime.datetime.now()
        if  now.hour!=0 and now.minute!=0:
            print(now.strftime('%Y-%m-%d %H:%M:%S'))
            time.sleep(1)
        else:
            pass




def create_app(config_name):
    app=Flask(__name__)

    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    bootstrap.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    mdb.init_app(app)
    scheduler.init_app(app)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint,url_prefix='/auth')
    #
    # data_profile()#数据准备
    scheduler.start()


    return app
