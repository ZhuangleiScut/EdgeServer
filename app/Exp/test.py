import os
import cv2
from flask import current_app
from keras.models import load_model
import numpy as np

from app.image.utils.datasets import get_labels
from app.image.utils.inference import load_detection_model, detect_faces, apply_offsets, draw_bounding_box, draw_text, \
    load_image
from app.image.utils.preprocessor import preprocess_input
import cv2
import dlib
import numpy
from imutils import face_utils


def shape_to_np(shape):
    # initialize the list of (x, y)-coordinates
    coords = numpy.zeros((shape.num_parts, 2), dtype=int)

    # loop over all facial landmarks and convert them
    # to a 2-tuple of (x, y)-coordinates
    for i in range(0, shape.num_parts):
        coords[i] = (shape.part(i).x, shape.part(i).y)

    # return the list of (x, y)-coordinates
    return coords


# GET INTERSECTION BETWEEN TWO LINES WITH COORDINATES ([x1,x2],[x2,y2])([x3,y3][x4,y4])
def get_intersection(x1, y1, x2, y2, x3, y3, x4, y4):
    denom = float(y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
    # if denom == 0 there is no slope, but in our case there will always be
    ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
    # ub = float((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom
    x = x1 + ua * (x2 - x1)
    y = y1 + ua * (y2 - y1)
    return (int(x), int(y))


def scale_faceangle(points, scale=1, offset=(0, 0)):
    mid = numpy.mean(points, axis=0)
    pts = []
    for i in range(len(points)):
        pts.append(
            tuple(
                numpy.array(
                    (numpy.subtract(
                        numpy.add(numpy.subtract(points[i], mid) * scale, mid),
                        offset)),
                    dtype=int)))
    return pts


def dealImage(image_path):
    basedir = os.path.abspath(os.path.dirname(__file__))
    detection_model_path = basedir + '/trained_models/detection_models/haarcascade_frontalface_default.xml'
    print(detection_model_path)
    emotion_model_path = basedir + '/trained_models/emotion_models/fer2013_mini_XCEPTION.102-0.66.hdf5'
    gender_model_path = basedir + '/trained_models/gender_models/simple_CNN.81-0.96.hdf5'
    dlib_model_path = basedir + '/trained_models/shape_predictor_68_face_landmarks.dat'

    emotion_labels = get_labels('fer2013')
    gender_labels = get_labels('imdb')
    font = cv2.FONT_HERSHEY_SIMPLEX

    # hyper-parameters for bounding boxes shape
    gender_offsets = (30, 60)
    gender_offsets = (10, 10)
    emotion_offsets = (20, 40)
    emotion_offsets = (0, 0)

    # loading models
    face_detection = load_detection_model(detection_model_path)
    emotion_classifier = load_model(emotion_model_path, compile=False)
    gender_classifier = load_model(gender_model_path, compile=False)

    # getting input model shapes for inference
    emotion_target_size = emotion_classifier.input_shape[1:3]
    gender_target_size = gender_classifier.input_shape[1:3]

    shape_predictor = dlib.shape_predictor(dlib_model_path)
    detector = dlib.get_frontal_face_detector()

    # loading images
    # rgb_image = load_image(image_path, grayscale=False)
    rgb_image = cv2.imread(image_path)
    # gray_image = load_image(image_path, grayscale=True)
    # gray_image = np.squeeze(gray_image)
    # gray_image = gray_image.astype('uint8')

    gray = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2GRAY)

    rects = detector(gray, 1)
    print('识别人脸数:' + str(len(rects)))

    # 总人数total
    total = len(rects)
    # loop over the face detections每张人脸
    for (i, rect) in enumerate(rects):
        # print('检测到人脸:')
        l = rect.left()
        r = rect.right()
        t = rect.top()
        b = rect.bottom()
        # print(l, r, t, b)
        roiImage = rgb_image[t:b, l:r]
        roiImage_gray = cv2.cvtColor(roiImage, cv2.COLOR_BGR2GRAY)
        # cv2.imwrite('sss.jpg', roiImage)

        # 获取脸部特征点
        shape = shape_predictor(gray, rect)
        # shape = face_utils.shape_to_np(shape)

        # 脸部特征点numpy
        shape_np = shape_to_np(shape)
        ################################################################################################
        # LEFTEST EYE POINT
        eyeL = tuple(shape_np[36])
        # RIGHTEST EYE POINT
        eyeR = tuple(shape_np[45])
        # MIDDLE EYE POINT
        eyeM = tuple(shape_np[27])
        # NOSE TOP POINT
        noseT = tuple(numpy.mean((numpy.mean((shape_np[21], shape_np[22]), axis=0), eyeM), axis=0))

        # NOSE BOTTOM POINT
        noseB = tuple(shape_np[33])
        # UPPER LIP BOTTOM MID POINT
        lipU = tuple(shape_np[62])
        # LOWER LIP TOP MID POINT
        lipL = tuple(shape_np[66])

        # CHIN BOTTOM POINT
        chinB = tuple(shape_np[8])
        tmp = numpy.subtract(numpy.mean((shape_np[6], shape_np[9]), axis=0), chinB)
        # CHIN LEFT POINT; CALCULATING MORE PRECISE ONE
        chinL = tuple(numpy.subtract(numpy.mean((shape_np[6], shape_np[7]), axis=0), tmp))
        # CHIN RIGHT POINT; CALCULATING MORE PRECISE ONE
        chinR = tuple(numpy.subtract(numpy.mean((shape_np[9], shape_np[10]), axis=0), tmp))

        # THE DIFFERENCE (eyeM - chinB) EQUALS 2/3 OF THE FACE
        tmp = numpy.subtract(eyeM, chinB)
        # GET 1/3 OF THE FACE
        tmp = tuple([int(x / 2) for x in tmp])

        # CALCULATING THE EDGES FOR THE BOX WE ARE GOING TO DRAW
        # EDGE POINT TOP LEFT, LEFT EYEBROW + 1/3 OF THE FACE SO WE GET THE FOREHEAD LINE
        edgeTL = tuple(numpy.add(shape_np[19], tmp))
        # EDGE POINT TOP RIGHT, RIGHT EYEBROW + 1/3 OF THE FACE SO WE GET THE FOREHEAD LINE
        edgeTR = tuple(numpy.add(shape_np[24], tmp))

        # MOVE THE TOP LEFT EDGE LEFT IN LINE WITH THE CHIN AND LEFT EYE - ESTIMATING FOREHEAD WIDTH
        edgeTL = get_intersection(edgeTL[0], edgeTL[1], edgeTR[0], edgeTR[1], eyeL[0],
                                  eyeL[1], chinB[0], chinB[1])

        # MOVE THE TOP RIGHT EDGE RIGHT IN LINE WITH THE CHIN AND RIGHT EYE - ESTIMATING FOREHEAD WIDTH
        edgeTR = get_intersection(edgeTR[0], edgeTR[1], edgeTL[0], edgeTL[1], eyeR[0],
                                  eyeR[1], chinB[0], chinB[1])

        tmp = numpy.subtract(eyeM, chinB)

        # EDGE POINT BOTTOM LEFT, CALCULATE HORIZONTAL POSITION
        edgeBL = tuple(numpy.subtract(edgeTL, tmp))
        # EDGE POINT BOTTOM RIGHT, CALCULATE HORIZONTAL POSITION
        edgeBR = tuple(numpy.subtract(edgeTR, tmp))

        # EDGE POINT BOTTOM LEFT, CALCULATE VERTICAL POSITION - IN LINE WITH CHIN SLOPE
        edgeBL = get_intersection(edgeTL[0], edgeTL[1], edgeBL[0], edgeBL[1], chinL[0], chinL[1],
                                  chinR[0], chinR[1])
        # EDGE POINT BOTTOM RIGHT, CALCULATE VERTICAL POSITION - IN LINE WITH CHIN SLOPE
        edgeBR = get_intersection(edgeTR[0], edgeTR[1], edgeBR[0], edgeBR[1], chinR[0], chinR[1],
                                  chinL[0], chinL[1])

        # CALCULATE HEAD MOVEMENT OFFSET FROM THE CENTER, lipU - lipL IS THE DISTANCE FROM BOTH LIPS (IN CASE MOUTH IS OPEN)
        offset = (float(noseT[0] - 2 * noseB[0] + chinB[0] + lipU[0] - lipL[0]),
                  float(noseT[1] - 2 * noseB[1] + chinB[1] + lipU[1] - lipL[1]))

        # BACKGROUND RECTANGLE
        recB = (edgeTL, edgeTR, edgeBR, edgeBL)

        # FOREBACKGROUND RECTANGLE
        recF = (scale_faceangle((recB), 1.1, offset))
        #
        # 脸部特征点
        # for (x, y) in shape_np:
        #     cv2.circle(rgb_image, (x, y), 1, (255, 0, 255), 5)

        # 背景框
        cv2.polylines(rgb_image, numpy.array([recB], numpy.int32), True,
                      (255, 0, 0), 5)

        # 画边
        for d in range(4):
            cv2.line(rgb_image, recB[d], recF[d], (255, 255, 0), 5)

        # 鼻子方向
        cv2.line(
            rgb_image, tuple(shape_np[30]),
            tuple(
                numpy.array(
                    (numpy.subtract(shape_np[30], offset)), dtype=int)),
            (0, 255, 255), 5)

        # 外框
        cv2.polylines(rgb_image, numpy.array([recF], numpy.int32), True,
                      (0, 255, 0), 5)

        ####################################################################################
        try:
            rgb_face = cv2.resize(roiImage, (gender_target_size))
            gray_face = cv2.resize(roiImage_gray, (emotion_target_size))
        except:
            continue

        rgb_face = preprocess_input(rgb_face, False)
        rgb_face = np.expand_dims(rgb_face, 0)
        gender_prediction = gender_classifier.predict(rgb_face)
        gender_label_arg = np.argmax(gender_prediction)
        gender_text = gender_labels[gender_label_arg]

        gray_face = preprocess_input(gray_face, True)
        gray_face = np.expand_dims(gray_face, 0)
        gray_face = np.expand_dims(gray_face, -1)
        emotion_label_arg = np.argmax(emotion_classifier.predict(gray_face))
        emotion_text = emotion_labels[emotion_label_arg]

        if gender_text == gender_labels[0]:
            color = (0, 0, 255)
        else:
            color = (255, 0, 0)

        # draw_bounding_box(rect, rgb_image, color)
        draw_text(r, t, rgb_image, gender_text, color, 0, -20, 1, 2)
        draw_text(r, t, rgb_image, emotion_text, color, 0, -50, 1, 2)
        print(gender_text)
        print(emotion_text)

        cv2.imshow('Frame', rgb_image)
        cv2.imwrite('do.jpg', rgb_image)
        # PRESS ESCAPE TO EXIT
        if cv2.waitKey(1) == 27:
            break


if __name__ == '__main__':
    dealImage('277.jpg')
