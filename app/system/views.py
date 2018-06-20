#! /usr/bin/env python
# -*- coding: utf-8 -*-
import re
from flask import render_template, redirect, request, url_for, current_app, abort, jsonify, session, flash
from flask_login import login_user, logout_user, current_user
from datetime import datetime
import json
from ..models import User, Log
from ..util.authorize import admin_login
from ..util.file_manage import get_file_type
from PIL import Image
import os
from ..util.utils import get_login_data, clear_session_cookie
from .. import db
import time
from . import system


@system.route('/')
@admin_login
def get_system_msg():
    """获取当前系统运行情况"""
    if request.method == 'POST':
        # 获取发送方ip地址
        rasp_ip = request.remote_addr
        print(rasp_ip)

        upload_file = request.files['file']
        # 传过来的文件名字
        old_file_name = upload_file.filename
        print(basedir)
        if upload_file:
            file_path = os.path.join(current_app.config['IMAGE_FOLDER'], old_file_name)
            upload_file.save(file_path)
            print(file_path)
            print("success")
            # print('file saved to %s' % file_path)
            return 'success'
        else:
            return 'failed'

    else:
        return 'Please upload image!'
