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

def getHeadPose(face_coordinates):
    shape_predictor = dlib.shape_predictor(
        "shape_predictor_68_face_landmarks.dat")
    # determine the facial landmarks for the face region, then
    # convert the facial landmark (x, y)-coordinates to a NumPy array
    shape = shape_predictor(gray, face)
    # PREDICT FACE LANDMARKS AND CONVERT THEM TO NUMPY ARRAY COORDINATES
    shape = shape_to_np(shape_predictor(gray, face))

    for i in range(1, 7):
        # LEFTEST EYE POINT
        eyeL = tuple(shape[36])
        # RIGHTEST EYE POINT
        eyeR = tuple(shape[45])
        # MIDDLE EYE POINT
        eyeM = tuple(shape[27])
        # NOSE TOP POINT
        noseT = tuple(numpy.mean((numpy.mean((shape[21], shape[22]), axis=0), eyeM), axis=0))

        # NOSE BOTTOM POINT
        noseB = tuple(shape[33])
        # UPPER LIP BOTTOM MID POINT
        lipU = tuple(shape[62])
        # LOWER LIP TOP MID POINT
        lipL = tuple(shape[66])

        # CHIN BOTTOM POINT
        chinB = tuple(shape[8])
        tmp = numpy.subtract(numpy.mean((shape[6], shape[9]), axis=0), chinB)
        # CHIN LEFT POINT; CALCULATING MORE PRECISE ONE
        chinL = tuple(numpy.subtract(numpy.mean((shape[6], shape[7]), axis=0), tmp))
        # CHIN RIGHT POINT; CALCULATING MORE PRECISE ONE
        chinR = tuple(numpy.subtract(numpy.mean((shape[9], shape[10]), axis=0), tmp))

        # THE DIFFERENCE (eyeM - chinB) EQUALS 2/3 OF THE FACE
        tmp = numpy.subtract(eyeM, chinB)
        # GET 1/3 OF THE FACE
        tmp = tuple([int(x / 2) for x in tmp])

        # CALCULATING THE EDGES FOR THE BOX WE ARE GOING TO DRAW
        # EDGE POINT TOP LEFT, LEFT EYEBROW + 1/3 OF THE FACE SO WE GET THE FOREHEAD LINE
        edgeTL = tuple(numpy.add(shape[19], tmp))
        # EDGE POINT TOP RIGHT, RIGHT EYEBROW + 1/3 OF THE FACE SO WE GET THE FOREHEAD LINE
        edgeTR = tuple(numpy.add(shape[24], tmp))

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
        offset = (float(noseT[0] - 2 * noseB[0] + chinB[0] + lipU[0] - lipL[0]) * 4,
                  float(noseT[1] - 2 * noseB[1] + chinB[1] + lipU[1] - lipL[1]) * 4)

        # BACKGROUND RECTANGLE
        recB = (edgeTL, edgeTR, edgeBR, edgeBL)

        # FOREBACKGROUND RECTANGLE
        recF = (scale_faceangle((recB), 1.5, offset))

        # DRAW FACIAL LANDMARK COORDINATES
        for (x, y) in shape:
            cv2.circle(frame, (x, y), 1, (255, 0, 255), 5)

        # DRAW BACKGROUND RECTANGLE
        cv2.polylines(frame, numpy.array([recB], numpy.int32), True,
                      (255, 0, 0), 5)

        # DRAW FACE BOX EDGE LINES
        for i in range(4):
            cv2.line(frame, recB[i], recF[i], (255, 255, 0), 5)

        # DRAW NOSE DIRECTION LINE
        cv2.line(
            frame, tuple(shape[30]),
            tuple(
                numpy.array(
                    (numpy.subtract(shape[30], offset)), dtype=int)),
            (0, 255, 255), 5)

        # DRAW FOREGROUNDBACKGROUND RECTANGLE
        cv2.polylines(frame, numpy.array([recF], numpy.int32), True,
                      (0, 255, 0), 5)



def dealImage(image_path):
    basedir = os.path.abspath(os.path.dirname(__file__))
    detection_model_path = basedir + '/trained_models/detection_models/haarcascade_frontalface_default.xml'
    print(detection_model_path)
    emotion_model_path = basedir + '/trained_models/emotion_models/fer2013_mini_XCEPTION.102-0.66.hdf5'
    gender_model_path = basedir + '/trained_models/gender_models/simple_CNN.81-0.96.hdf5'
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

    # loading images
    rgb_image = load_image(image_path, grayscale=False)
    gray_image = load_image(image_path, grayscale=True)
    gray_image = np.squeeze(gray_image)
    gray_image = gray_image.astype('uint8')

    # face_area
    # face_area = 0

    faces = detect_faces(face_detection, gray_image)
    for face_coordinates in faces:
        x1, x2, y1, y2 = apply_offsets(face_coordinates, gender_offsets)
        rgb_face = rgb_image[y1:y2, x1:x2]

        x1, x2, y1, y2 = apply_offsets(face_coordinates, emotion_offsets)
        gray_face = gray_image[y1:y2, x1:x2]

        try:
            rgb_face = cv2.resize(rgb_face, (gender_target_size))
            gray_face = cv2.resize(gray_face, (emotion_target_size))
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

        draw_bounding_box(face_coordinates, rgb_image, color)
        draw_text(face_coordinates, rgb_image, gender_text, color, 0, -20, 1, 2)
        draw_text(face_coordinates, rgb_image, emotion_text, color, 0, -50, 1, 2)

        # area = abs(x1 - x2) * abs(y1 - y2)
        # face_area += area

    bgr_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
    # cv2.imwrite('../images/predicted_test_image.png', bgr_image)
    file_path = os.path.join(current_app.config['RESULT_FOLDER'], 'doing.jpg')
    print(file_path)
    cv2.imwrite(file_path, bgr_image)
