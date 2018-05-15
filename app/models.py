#! /usr/bin/env python
# -*- coding: utf-8 -*-


from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app
from . import db, login_manager

""" 用户管理
@User:用户登录、注册、认证邮箱等
"""

# 用户默认配额
DEFAULT_CPU = 1000
DEFAULT_MEMORY = 2048
DEFAULT_APPS = 10
DEFAULT_GPU = 0


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)

    # 用户名、密码与邮箱，以邮箱作为登录主要凭据
    username = db.Column(db.String(128), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), unique=True, index=True, nullable=False)
    confirmed = db.Column(db.Boolean, default=False, nullable=False)

    # 基本信息
    description = db.Column(db.String(128))
    real_name = db.Column(db.String(128))
    phone = db.Column(db.String(128))
    address = db.Column(db.String(128))
    last_login = db.Column(db.DateTime(), default=datetime.now)
    date_joined = db.Column(db.DateTime(), default=datetime.now)
    permissions = db.Column(db.Integer, default=1, nullable=False)  # 权限控制：管理员0, 用户1

    # 业务信息
    is_auth = db.Column(db.Integer, default=0, nullable=False)      # 是否被管理员通过认证。默认为0(未认证), 1(已认证)
    avatar_url = db.Column(db.String(128))                          # 头像路径，建议设置为一个本地的相对路径的URL
    api_password = db.Column(db.String(128))                        # API后台账户的密码(建议随机生成8位密码),且此密码对用户不可见,以防止不良用户对后台的非法访问

    ehpc_flag = db.Column(db.Integer, default=0, nullable=False)    # 若该值为1，则标志该用户是否是来自ehpc系统的一个用户

    # 资源配额, 注意管理员用户也有资源配额限制
    max_cpu = db.Column(db.Integer, default=DEFAULT_CPU)                    # 资源配额：CPU 核数，单位为千分之一
    used_cpu = db.Column(db.Integer, default=0)
    max_memory = db.Column(db.Integer, default=DEFAULT_MEMORY)              # 资源配额：内存大小，单位为兆（M）
    used_memory = db.Column(db.Integer, default=0)
    max_gpu = db.Column(db.Integer, default=DEFAULT_GPU)                    # 资源配额：GPU 核数，单位为千分之一
    used_gpu = db.Column(db.Integer, default=0)
    max_apps = db.Column(db.Integer, default=DEFAULT_APPS)                  # 资源配额：可创建的容器数量
    used_apps = db.Column(db.Integer, default=0)

    applies = db.relationship('Apply', backref='user', lazy='dynamic')
    tempInstances = db.relationship('TempInstance', backref='user', lazy='dynamic')

    # 以下函数分别用于对用户密码进行读取保护、散列化以及验证密码
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    @property
    def raw_password(self):
        raise AttributeError('password is not a readable attribute')

    @raw_password.setter
    def raw_password(self, password):
        """用于直接存储来自ehpc的密码哈希"""
        self.password_hash = password

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    # 以下两个函数用于token的生成和校验
    def generate_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'id': self.id})

    @staticmethod
    def verify_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        uid = data.get('id')
        if uid:
            return User.query.get(uid)
        return None


# 插件flask_login的回调函数，用于读取用户
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


"""
资源管理
@Apply:配额的申请表
用户申请增加配额，通过管理员审核后即可增加相应的配额
"""


class Apply(db.Model):
    __tablename__ = 'apply'
    id = db.Column(db.Integer, primary_key=True)
    userId = db.Column(db.Integer, db.ForeignKey('users.id'))
    instance_num = db.Column(db.Integer)                  # 申请的实例数量
    cpu_num = db.Column(db.Integer)                       # 申请的CPU核数，单位是千分之一
    memory_num = db.Column(db.Integer)                    # 申请的内存数量，单位是M
    gpu_num = db.Column(db.Integer, default=0)            # 申请的GPU核数，单位是千分之一
    note = db.Column(db.Text())                           # 备注、申请理由
    status = db.Column(db.Integer, default=0)             # 审核状态,0是待审核，1是通过，2是不通过
    created_time = db.Column(db.DateTime(), default=datetime.now)
    auth_time = db.Column(db.DateTime(), nullable=True)


"""
实例管理
@TempInstance：存储被删除实例的伪暂停表
"""


class TempInstance(db.Model):
    __tablename__ = 'tempinstances'
    id = db.Column(db.Integer, primary_key=True)
    userId = db.Column(db.Integer, db.ForeignKey('users.id'))         # 所属用户
    appId = db.Column(db.Integer, db.ForeignKey('applications.id'))   # 所属应用模板
    name = db.Column(db.String(128), nullable=False)                  # 实例名
    param = db.Column(db.Text(), nullable=False)                      # 启动参数
    cpu_num = db.Column(db.Integer)                                   # CPU消耗量
    memory_num = db.Column(db.Integer)                                # 内存消耗量
    apps_num = db.Column(db.Integer)                                  # 容器数量消耗量
    created_time = db.Column(db.DateTime(), default=datetime.now)     # 暂停时间


"""
模板管理
@Application:模板
由于不同的模板可能具有不同的自定义参数，因此用一个json字符串来表示
"""


class Application(db.Model):
    __tablename__ = 'applications'
    id = db.Column(db.Integer, primary_key=True)                # 应用ID（注意，非k8s端ID）
    aid = db.Column(db.Integer)                                 # k8s端的应用ID
    name = db.Column(db.String(128), nullable=False)            # 模板中文名
    info = db.Column(db.Text(), nullable=False)                 # 模板中文简介
    param = db.Column(db.Text(), nullable=False)                # 模板参数自定义json字符串
    path = db.Column(db.String(128))                            # 模板的后台路径
    param_guide = db.Column(db.Text())                          # 创建实例时提供给用户的对各个参数的集中解释说明
    cover_img = db.Column(db.String(128), default='/static/resource/img/test2.jpg')    # 封面图片地址
    updatedTime = db.Column(db.DateTime(), default=datetime.now)  # 更新时间

    tempInstances = db.relationship('TempInstance', backref='application', lazy='dynamic')


"""
资讯类管理
@News：新闻资讯
@Notices：系统公告
"""


class News(db.Model):
    __tablename__ = 'news'
    id = db.Column(db.Integer, primary_key=True)                  # 资讯 ID
    title = db.Column(db.String(128), nullable=False)             # 资讯标题
    poster = db.Column(db.String(128), nullable=False)            # 发布者
    content = db.Column(db.Text(), nullable=False)                # 资讯正文
    visitNum = db.Column(db.Integer, default=0)                   # 浏览次数
    updatedTime = db.Column(db.DateTime(), default=datetime.now)  # 更新时间


class Notice(db.Model):
    __tablename__ = 'notices'
    id = db.Column(db.Integer, primary_key=True)                  # 公告 ID
    title = db.Column(db.String(128), nullable=False)             # 公告标题
    poster = db.Column(db.String(128), nullable=False)            # 发布者
    content = db.Column(db.Text(), nullable=False)                # 公告正文
    visitNum = db.Column(db.Integer, default=0)                   # 浏览次数
    updatedTime = db.Column(db.DateTime(), default=datetime.now)  # 更新时间

