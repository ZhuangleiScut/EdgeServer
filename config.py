"""
配置文件
config.py 是初始化 Flask app 的配置文件,当创建一个 app 时,将选择一种配置进行初始化
项目用到的全局变量也写在这个文件中,主要包括多种模式下的配置类型和全局参数（如密钥、连接数据库的 URL）等

config.py、APP/init.py 以及 manage.py 之间的关系：
1. config.py 是创建app时需参考的配置文件,即使用何种配置（生产环境或开发环境）
2. app/init.py 是创建app的具体工厂函数，并包括了路由的配置。该文件使用了config.py中的配置。
3. manage.py 是创建以及运行app的一个通用脚本，该文件使用了 APP/init.py
"""
import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # 此处定义全局变量
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'zl12345678'  # 设置密钥，可能会用在某些涉及到加解密的功能中
    SQLALCHEMY_TRACK_MODIFICATIONS = True                      # 该项不设置为True的话可能会导致数据库报错

    # 头像的存储路径与默认头像路径
    AVATAR_PATH = 'static/upload/avatar/'
    AVATAR_FOLDER = os.path.join(basedir, 'APP/', AVATAR_PATH)
    DEFAULT_AVATAR = '/static/resource/img/none.jpg'

    IMAGE_PATH = 'static/upload/image/'
    IMAGE_FOLDER = os.path.join(basedir, 'APP/', IMAGE_PATH)
    # 应用模板封面的存储路径
    APPLICATION_PATH = 'static/upload/application'
    APPLICATION_FOLDER = os.path.join(basedir, 'APP/', APPLICATION_PATH)

    # 安全设置
    SSL_DISABLE = False
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True

    # 邮箱设置
    MAIL_SERVER = 'smtp.qq.com'
    MAIL_PORT = 25
    MAIL_USE_TLS = True
    MAIL_USERNAME = '2697950380@qq.com'
    MAIL_PASSWORD = '467540415'
    FLASKY_MAIL_SUBJECT_PREFIX = '[Flasky]'
    FLASKY_MAIL_SENDER = 'Flasky Admin <2697950380@qq.com.com>'

    FLASKY_ADMIN = os.environ.get('FLASKY_ADMIN')
    FLASKY_SLOW_DB_QUERY_TIME = 0.5

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    # 连接测试环境数据库的URL
    SQLALCHEMY_DATABASE_URI = (os.environ.get('DEV_DATABASE_URL') or
                               'mysql://root:1314@localhost/edgeserver_dev')


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = (os.environ.get('DEV_DATABASE_URL') or
                               'mysql://root:2018@localhost/edgeserver_test')
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False
    # 连接生产环境数据库的URL
    SQLALCHEMY_DATABASE_URI = (os.environ.get('DEV_DATABASE_URL') or
                               'mysql://root:2018@localhost/edgeserver_pro')


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
