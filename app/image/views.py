#! /usr/bin/env python
# -*- coding: utf-8 -*-
from flask import request, current_app, abort
import os
from . import image
import logging
from . import detector
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
        # print(basedir)
        if upload_file:
            file_path = os.path.join(current_app.config['IMAGE_FOLDER'], old_file_name)
            upload_file.save(file_path)
            print(file_path)
            print("success")
            try:
                # ret, frame = cv2.imread(file_path)
                detector.dealImage(file_path)
            except Exception as err:
                logging.error('An error has occurred whilst processing the file: "{0}"'.format(err))
                abort(400)
            return 'success'
        else:
            return 'failed'

    else:
        return 'Please upload image!'
