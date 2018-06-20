"""
    本文件是项目本身的构造文件
    主要包括创建 flask app 的工厂函数
    配置 Flask 扩展插件时往往在工厂函数中对 app 进行相关的初始化。
"""

from flask import Flask
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import config
import pymysql
pymysql.install_as_MySQLdb()


mail = Mail()
db = SQLAlchemy()

login_manager = LoginManager()
login_manager.session_protection = 'strong'  # 设置session保护级别
login_manager.login_view = 'admin.login'      # 设置登录视图


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    mail.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)

    # 注册路由
    from .admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')

    from .image import image as image_blueprint
    app.register_blueprint(image_blueprint, url_prefix='/image')

    from .system import system as system_blueprint
    app.register_blueprint(system_blueprint, url_prefix='/system')

    return app
