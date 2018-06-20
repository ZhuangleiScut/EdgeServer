#! /usr/bin/env python
# -*- coding: utf-8 -*-
import re

import cv2
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
from . import image
from .. import db
import time
from . import emotion_gender_processor as eg_processor
import logging
basedir = os.path.abspath(os.path.dirname(__file__))


@image.route('/', methods=['GET', 'POST'])
def get_frame():
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
            try:
                # ret, frame = cv2.imread(file_path)
                eg_processor.dealImage(file_path)
            except Exception as err:
                logging.error('An error has occurred whilst processing the file: "{0}"'.format(err))
                abort(400)
            return 'success'
        else:
            return 'failed'

    else:
        return 'Please upload image!'
