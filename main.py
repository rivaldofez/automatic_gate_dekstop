import sys
import platform
from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *

from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.models import load_model
from imutils.video import VideoStream
import numpy as np
import imutils
import time
import cv2
import os


# GUI FILE
from app_modules import *

class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.prototxtPath = r"face_detector\deploy.prototxt"
        self.weightsPath = r"face_detector\res10_300x300_ssd_iter_140000.caffemodel"
        self.faceNet = cv2.dnn.readNet(self.prototxtPath, self.weightsPath)
        self.maskNet = load_model("mask_detector.model")
        self.capture = cv2.VideoCapture(0)

        # QTimer
        self.timer = QTimer()
        self.timer.timeout.connect(lambda: self.runVideo())
        self.timer.start(10)

        #Print Versi Sistem
        print('Sistem: ' + platform.system())
        print('Versi: ' +platform.release())

        #Remove standar title bar
        UIFunctions.removeTitleBar(True)

        #Set Judul Window dam label
        self.setWindowTitle('Automatic Gate')
        UIFunctions.labelTitle(self, 'Automatic Gate')
        UIFunctions.labelDescription(self, 'Menu')

        #Set Ukuran minimum window
        startSize = QSize(800, 400)
        self.resize(startSize)
        self.setMinimumSize(startSize)
        # UIFunctions.enableMaximumSize(self, 500, 720)

        #Membuat Menu
        #Ukuran Toggle
        self.ui.btn_toggle_menu.clicked.connect(lambda: UIFunctions.toggleMenu(self, 180, True))

        #Menambahkan Menu
        self.ui.stackedWidget.setMinimumWidth(20)
        UIFunctions.addNewMenu(self, "Home", "btn_home", "url(:/16x16/icons/16x16/cil-home.png)", True)
        UIFunctions.addNewMenu(self, "Calibrate", "btn_widgets", "url(:/16x16/icons/16x16/cil-equalizer.png)", True)
        # UIFunctions.addNewMenu(self, "Custom Widgets", "btn_widgets", "url(:/16x16/icons/16x16/cil-user-follow.png)", False)

        #Default Start Menu Button dan Pages
        UIFunctions.selectStandardMenu(self, "btn_home")
        self.ui.stackedWidget.setCurrentWidget(self.ui.page_home)


        #Button Calibrates
        self.ui.btn_Calibration.clicked.connect(lambda: self.Calibrates())
 
        #Button Threshold
        self.ui.btn_Threshold.clicked.connect(lambda: self.Threshold())


        # Fungsi move window
        def moveWindow(event):
            # Fullscreen ke normal size
            if UIFunctions.returStatus() == 1:
                UIFunctions.maximize_restore(self)

            # Move window
            if event.buttons() == Qt.LeftButton:
                self.move(self.pos() + event.globalPos() - self.dragPos)
                self.dragPos = event.globalPos()
                event.accept()

        # Widget untuk move window
        self.ui.frame_label_top_btns.mouseMoveEvent = moveWindow

        #Load definitions (untuk replace konfigurasi bawaan)
        UIFunctions.uiDefinitions(self)

        #Show Windows
        self.show()

        #End Init....


    def Calibrates(self):
        valCalibration = self.ui.editCalibration.text()
        self.ui.labelCalibration.setText(valCalibration)

    def Threshold(self):
        valThreshold = self.ui.editThreshold.text()
        self.ui.labelThreshold.setText(valThreshold)

    #Fungsi Button Menu
    def Button(self):
        #Button di klik
        btnWidget = self.sender()

        #Page Home
        if btnWidget.objectName() == "btn_home":
            self.ui.stackedWidget.setCurrentWidget(self.ui.page_home)
            UIFunctions.resetStyle(self, "btn_home")
            UIFunctions.labelPage(self, "Home")
            btnWidget.setStyleSheet(UIFunctions.selectMenu(btnWidget.styleSheet()))

        #Page Widgets/Calibrate
        if btnWidget.objectName() == "btn_widgets":
            self.ui.stackedWidget.setCurrentWidget(self.ui.page_widgets)
            UIFunctions.resetStyle(self, "btn_widgets")
            UIFunctions.labelPage(self, "Custom Widgets")
            btnWidget.setStyleSheet(UIFunctions.selectMenu(btnWidget.styleSheet()))

    #Event Mouse Double Click
    def eventFilter(self, watched, event):
        if watched == self.le and event.type() == QtCore.QEvent.MouseButtonDblClick:
            print("pos: ", event.pos())

    #Event Mouse Click
    def mousePressEvent(self, event):
        self.dragPos = event.globalPos()
        if event.buttons() == Qt.LeftButton:
            print('Mouse click: LEFT CLICK')
        if event.buttons() == Qt.RightButton:
            print('Mouse click: RIGHT CLICK')
        if event.buttons() == Qt.MidButton:
            print('Mouse click: MIDDLE BUTTON')

    #Event Keyborad press
    def keyPressEvent(self, event):
        print('Key: ' + str(event.key()) + ' | Text Press: ' + str(event.text()))

    #Event resize
    def resizeEvent(self, event):
        self.resizeFunction()
        return super(MainWindow, self).resizeEvent(event)

    def resizeFunction(self):
        print('Height: ' + str(self.height()) + ' | Width: ' + str(self.width()))



    def detect_and_predict_mask(self,frame, faceNet, maskNet):
        # mendefinisikan ukuran frame dan buat kedalam tipe blob

        (h, w) = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 1.0, (224, 224),
                                     (104.0, 177.0, 123.0))

        # memasukkan tipe frame dalam bentuk blob ke neural net untuk mendeteksi wajah
        faceNet.setInput(blob)
        detections = faceNet.forward()
        print(detections.shape)

        # inisialisasi list wajah, lalu menentukan lokasi (kotak")
        # inisialisasi list prediksi dari neural net face sebelumnya
        faces = []
        locs = []
        preds = []

        # looping untuk deteksi
        for i in range(0, detections.shape[2]):
            # ekstrak tingkat kepercayaan (probabilitas dan akurasi)
            confidence = detections[0, 0, i, 2]

            # filter out weak detections by ensuring the confidence is
            # greater than the minimum confidence
            if confidence > 0.5:
                # compute the (x, y)-coordinates of the bounding box for
                # the object
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (startX, startY, endX, endY) = box.astype("int")

                # ensure the bounding boxes fall within the dimensions of
                # the frame
                (startX, startY) = (max(0, startX), max(0, startY))
                (endX, endY) = (min(w - 1, endX), min(h - 1, endY))

                # extract the face ROI, convert it from BGR to RGB channel
                # ordering, resize it to 224x224, and preprocess it
                face = frame[startY:endY, startX:endX]
                face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
                face = cv2.resize(face, (224, 224))
                face = img_to_array(face)
                face = preprocess_input(face)

                # add the face and bounding boxes to their respective
                # lists
                faces.append(face)
                locs.append((startX, startY, endX, endY))

        # only make a predictions if at least one face was detected
        if len(faces) > 0:
            # for faster inference we'll make batch predictions on *all*
            # faces at the same time rather than one-by-one predictions
            # in the above `for` loop
            faces = np.array(faces, dtype="float32")
            preds = maskNet.predict(faces, batch_size=32)

        # return a 2-tuple of the face locations and their corresponding
        # locations
        return (locs, preds)

    def runVideo(self):
        ret, frame = self.capture.read()

        # detect faces in the frame and determine if they are wearing a
        # face mask or not
        (locs, preds) = self.detect_and_predict_mask(frame, self.faceNet, self.maskNet)

        # loop over the detected face locations and their corresponding
        # locations
        for (box, pred) in zip(locs, preds):
            # unpack the bounding box and predictions
            (startX, startY, endX, endY) = box
            (mask, withoutMask) = pred

            # determine the class label and color we'll use to draw
            # the bounding box and text
            label = "Mask" if mask > withoutMask else "No Mask"
            color = (0, 255, 0) if label == "Mask" else (0, 0, 255)

            # include the probability in the label
            label = "{}: {:.2f}%".format(label, max(mask, withoutMask) * 100)

            # display the label and bounding box rectangle on the output
            # frame
            cv2.putText(frame, label, (startX, startY - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)
            cv2.rectangle(frame, (startX, startY), (endX, endY), color, 2)

        # show the output frame

        try:
            image = cv2.resize(frame, (400, 800))
        except Exception as e:
            print(e)
        qformat = QImage.Format_Indexed8
        if len(image.shape) == 3:
            if image.shape[2] == 4:
                qformat = QImage.Format_RGBA8888
            else:
                qformat = QImage.Format_RGB888
        outImage = QImage(image, image.shape[1], image.shape[0], image.strides[0], qformat)
        outImage = outImage.rgbSwapped()

        self.ui.imgLabel.setPixmap(QPixmap.fromImage(outImage))
        self.ui.imgLabel.setScaledContents(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    QtGui.QFontDatabase.addApplicationFont('fonts/segoeui.ttf')
    QtGui.QFontDatabase.addApplicationFont('fonts/segoeuib.ttf')
    window = MainWindow()
    sys.exit(app.exec_())
