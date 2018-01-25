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

    #日志信息按月存入redis
    log_list = list(event for date in date_list
                    for behave in date.events
                    for event in date.events[behave])
    logs_data = pd.DataFrame(log_list)
    dates = sorted(logs_data['date'])
    date_final = dates[len(dates) - 1]
    date_first = dates[0]

    #将日志范围存入redis
    # date_range = {'date_first':date_first,'date_final':date_final}
    # red.set('date_range', json.dumps(date_range))
    red.set('logs_data',DataFrame(logs_data).to_msgpack(compress='zlib'))
    # event_dict = {}
    # for year in range(date_first.year, date_final.year + 1):
    #     if year == date_first.year and year != date_final.year:
    #         for month in range(date_first.month, 13):
    #             event_dict['logs_data_%s-%s' % (year, month)] = logs_data.loc[
    #                 logs_data['date'].apply(lambda x: x.month == month and x.year == year)]
    #     elif year == date_first.year and year == date_final.year:
    #         for month in range(date_first.month, date_final.month + 1):
    #             event_dict['logs_data_%s-%s' % (year, month)] = logs_data.loc[
    #                 logs_data['date'].apply(lambda x: x.month == month and x.year == year)]
    #         break
    #     elif year != date_final.year:
    #         for month in range(1, 13):
    #             event_dict['logs_data_%s-%s' % (year, month)] = logs_data.loc[
    #                 logs_data['date'].apply(lambda x: x.month == month and x.year == year)]
    #     else:
    #         for month in range(1, date_final.month + 1):
    #             event_dict['logs_data_%s-%s' % (year, month)] = logs_data.loc[
    #                 logs_data['date'].apply(lambda x: x.month == month and x.year == year)]

    # for date in event_dict:
    #     red.set(date, DataFrame(event_dict[date]).to_msgpack(compress='zlib'))
    print('Logs Data Complete')

    #合同信息存入redis
    infolist = list(
        [case.case_id, case.case_status, float(case.amount) if case.amount else 0.0, float(case.loan_amount) if case.loan_amount else 0.0,case.sale_name,case.status_code,case.recommend_name,float(case.recommend_fee) if case.recommend_fee else 0.0,case.is_renew_case,] for case in
        cases)
    case_data = DataFrame(infolist)
    case_data.columns = ['case_id', 'status', 'amount', 'loan_amount','sale_name', 'status_code','recommend_name','recommend_fee','is_renew_case']
    case_data = case_data[~case_data['case_id'].isnull()]
    red.set('case_data', DataFrame(case_data).to_msgpack(compress='zlib'))
    print('Case Data Complete')

    #门店信息存入js
    shop_data = find_shop()  # 查询所有门店的名称
    shop_reflect = {}
    for shop_info in shop_data:
        shop_reflect[int(shop_info['id'])] = shop_info['abbreviation']
    shop_reflect.pop(7)  # 将测试门店除去
    shop=json.dumps(shop_reflect)
    red.set('shop_data', shop)
    print('Shop Data complete')



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
    data_profile()#数据准备
    scheduler.start()


    return app
