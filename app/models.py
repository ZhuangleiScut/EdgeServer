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
    avatar_url = db.Column(db.String(128))                          # 头像路径，建议设置为一个本地的相对路径的URL
    # 日志
    logs = db.relationship('Log', backref='user', lazy='dynamic')

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
设备管理
@equipment:设备列表
"""


class Equipment(db.Model):
    __tablename__ = 'equipment'
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(128))
    image_num = db.Column(db.Integer)                           # 树莓派上传的图片数量
    run_time = db.Column(db.DateTime(), default=datetime.now)   # 设备开始运行时间
    last_commit = db.Column(db.DateTime())                      # 最后一次上传的时间
    ip_addr = db.Column(db.String(128))
    image = db.relationship('Image', backref='equip')


"""
图片缓存管理
@Image：图片缓存列表
"""


class Image(db.Model):
    __tablename__ = 'image'
    id = db.Column(db.Integer, primary_key=True)
    equip_id = db.Column(db.Integer, db.ForeignKey('equipment.id'))        # 所属设备
    face_num = db.Column(db.Integer)                                  # 图片中包含的人脸个数
    commit_time = db.Column(db.DateTime(), default=datetime.now)      # 上传时间
    path = db.Column(db.String(128), nullable=False)                  # 图片存储路径
    face = db.relationship('Face', backref='image')

"""
脸部数据管理
@Face:脸部数据表
"""


class Face(db.Model):
    __tablename__ = 'face'
    id = db.Column(db.Integer, primary_key=True)                        # ID
    image_id = db.Column(db.Integer, db.ForeignKey('image.id'))     # 脸部所在的图片id
    # name = db.Column(db.String(128), nullable=False)            # 模板中文名
    # info = db.Column(db.Text(), nullable=False)                 # 模板中文简介
    # param = db.Column(db.Text(), nullable=False)                # 模板参数自定义json字符串
    # path = db.Column(db.String(128))                            # 模板的后台路径
    # param_guide = db.Column(db.Text())                          # 创建实例时提供给用户的对各个参数的集中解释说明
    # cover_img = db.Column(db.String(128), default='/static/resource/img/test2.jpg')    # 封面图片地址
    # updatedTime = db.Column(db.DateTime(), default=datetime.now)  # 更新时间


class Log(db.Model):
    __tablename__ = 'logs'
    id = db.Column(db.Integer, primary_key=True)
    userId = db.Column(db.Integer, db.ForeignKey('users.id'))                  # 操作涉及的用户
    content = db.Column(db.Text(), nullable=False)                             # 操作的主要内容
    """
    type_flag 用于记录操作类型:0代表普通操作如登录等,1代表删除图片缓存,2代表删除数据信息
    """
    type_flag = db.Column(db.Integer, default=0)
    created_time = db.Column(db.DateTime(), default=datetime.now)              # 记录日志时的时间,自动填充现在的时间
