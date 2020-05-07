from PyQt5.QtGui import QFont, QPainter
from PyQt5.QtCore import Qt, QUrl, QSize
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtWidgets import *

from video_editor.editor import VideoEditor
import threading


class VideoPlayer(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.videoPath = None
        self.videoDuration = None
        self.videoEditor = None

        # Font
        self.setFont(QFont("Noto Sans", 10))

        # Edit window
        self.editWindow = EditWidget(self)

        # Video widget and media player
        videoWidget = QVideoWidget()
        videoWidget.setStyleSheet('background: black')
        self.mediaPlayer = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.mediaPlayer.setVideoOutput(videoWidget)
        self.mediaPlayer.stateChanged.connect(self.mediaStateChanged)
        self.mediaPlayer.positionChanged.connect(self.positionChanged)
        self.mediaPlayer.durationChanged.connect(self.durationChanged)
        self.mediaPlayer.error.connect(self.handleError)

        # Play button
        self.playButton = QPushButton()
        self.playButton.setEnabled(False)
        self.playButton.setFixedHeight(24)
        self.playButton.setIconSize(QSize(16, 16))
        self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.playButton.clicked.connect(self.togglePlay)

        # Time slider
        self.positionSlider = QSliderMarker(Qt.Horizontal)
        self.positionSlider.setRange(0, 0)
        self.positionSlider.sliderMoved.connect(self.setPosition)

        # Time label
        self.timeLabel = QLabel("- - : - -")
        self.timeLabel.setAlignment(Qt.AlignTop)
        self.timeLabel.setFixedHeight(24)

        # Open button
        openButton = QPushButton("Open Video")
        openButton.setFixedHeight(24)
        openButton.clicked.connect(self.loadVideoFile)

        # Split button
        self.splitButton = QPushButton("Split")
        self.splitButton.setToolTip("Split interval in current time")
        self.splitButton.setEnabled(False)
        self.splitButton.setFixedHeight(24)
        self.splitButton.clicked.connect(self.split)

        # Export selected button
        self.exportAllButton = QPushButton("Export selected splits")
        self.exportAllButton.setToolTip("Join all selected splits in a single video file")
        self.exportAllButton.setEnabled(False)
        self.exportAllButton.setFixedHeight(24)
        self.exportAllButton.clicked.connect(self.exportVideo)

        # Status bar
        self.statusBar = QStatusBar()
        self.statusBar.setFixedHeight(24)
        self.statusBar.showMessage("Ready")

        # Controls layout [open, play and slider]
        controlLayout = QHBoxLayout()
        controlLayout.setContentsMargins(0, 0, 0, 0)
        controlLayout.addWidget(self.playButton)
        controlLayout.addWidget(self.positionSlider)
        controlLayout.addWidget(self.timeLabel)

        # Editor layout [split and export_all]
        editorLayout = QHBoxLayout()
        editorLayout.setContentsMargins(0, 0, 0, 0)
        editorLayout.addWidget(openButton)
        editorLayout.addWidget(self.splitButton)
        editorLayout.addWidget(self.exportAllButton)
        editorLayout.addStretch(1)

        # Splits layout
        self.splitsLayout = QHBoxLayout()
        self.splitsLayout.setContentsMargins(0, 0, 0, 0)
        self.splitsLayout.setSpacing(0)

        # General layout
        layout = QVBoxLayout()
        layout.addWidget(videoWidget)
        layout.addLayout(controlLayout)
        layout.addLayout(editorLayout)
        layout.addLayout(self.splitsLayout)
        layout.addWidget(self.statusBar)
        self.setLayout(layout)

    @staticmethod
    def positionToString(position):
        seconds = position // 1000
        return "{:02d}:{:02d}".format(seconds // 60, seconds % 60)

    def openEditWindow(self, splitId):
        config = self.videoEditor.get_split_config(splitId)
        self.editWindow.updateFields(splitId, config)
        self.editWindow.show()

    def loadVideoFile(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Choose video file", ".",
                                                  "Video Files (*.mp4 *.flv *.ts *.mkv *.avi)")

        if fileName != '':
            self.videoPath = fileName
            self.mediaPlayer.setMedia(QMediaContent(QUrl.fromLocalFile(fileName)))
            self.playButton.setEnabled(True)
            self.splitButton.setEnabled(True)
            self.exportAllButton.setEnabled(True)
            self.statusBar.showMessage(fileName)
            self.togglePlay()

    def getSplitWidgets(self):
        for i in range(self.splitsLayout.count()):
            yield self.splitsLayout.itemAt(i).widget()

    def updateSplitsGUI(self):
        oldWidgets = list(self.getSplitWidgets())

        splitTimes = []
        for i, split in enumerate(self.videoEditor.get_splits()):
            splitWgt = SplitWidget(self, i)
            splitWgt.setToolTip("{} - {}".format(self.positionToString(split.start_time),
                                                 self.positionToString(split.end_time)))
            splitWgt.setMinimumWidth(4)
            self.splitsLayout.addWidget(splitWgt, split.duration)
            splitTimes.append(split.start_time)

        for widget in oldWidgets:
            widget.setParent(None)

        self.positionSlider.splitValues = splitTimes
        self.positionSlider.update()

    def exportVideo(self):
        splitIds = []
        for splitWgt in self.getSplitWidgets():
            if splitWgt.marked:
                splitIds.append(splitWgt.splitId)

        if not splitIds:
            QMessageBox(QMessageBox.NoIcon, "No selected splits",
                        "You have to select at least one split to export a video", QMessageBox.NoButton, self).show()
            return

        videoExtension = self.videoPath.split(".")[-1]
        fileName, _ = QFileDialog.getSaveFileName(self, "Choose video file", ".",
                                                  "Video Files (*.{})".format(videoExtension))
        if fileName:
            t = threading.Thread(target=self.generateVideo, args=(splitIds, fileName))
            t.setDaemon(True)
            t.start()

    def generateVideo(self, splitIds, filename):
        self.setDisabled(True)
        self.mediaPlayer.pause()
        self.videoEditor.export_and_join_splits(splitIds, filename)
        self.setDisabled(False)

    def togglePlay(self):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.mediaPlayer.pause()
        else:
            self.mediaPlayer.play()

    def mediaStateChanged(self, state):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

    def positionChanged(self, position):
        # Media player positionChanged event, updates slider and timer
        self.positionSlider.setValue(position)
        self.timeLabel.setText(self.positionToString(position))

    def durationChanged(self, duration):
        # Triggers when a video is loaded
        self.positionSlider.setRange(0, duration)
        self.timeLabel.setText("00:00")
        self.videoDuration = duration
        self.videoEditor = VideoEditor(self.videoPath, self.videoDuration)
        self.updateSplitsGUI()

    def setPosition(self, position):
        # Slider setPosition event, updates media player and timer
        self.mediaPlayer.setPosition(position)
        self.timeLabel.setText(self.positionToString(position))
        if position < self.positionSlider.maximum() and self.mediaPlayer.state() != QMediaPlayer.PlayingState:
            self.mediaPlayer.play()

    def split(self):
        time = self.positionSlider.value()
        self.videoEditor.add_split(time)
        self.updateSplitsGUI()

    def handleError(self):
        self.playButton.setEnabled(False)
        self.splitButton.setEnabled(False)
        self.exportAllButton.setEnabled(False)
        self.statusBar.showMessage("Error: " + self.mediaPlayer.errorString())


class QSliderMarker(QSlider):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.splitValues = []

    def mousePressEvent(self, ev):
        newPosition = QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), ev.x(), self.width())
        self.setSliderPosition(newPosition)
        self.parent().setPosition(newPosition)

    def mouseMoveEvent(self, ev):
        newPosition = QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), ev.x(), self.width())
        self.setSliderPosition(newPosition)
        self.parent().setPosition(newPosition)

    def paintEvent(self, event):
        super().paintEvent(event)

        if self.maximum() == 0:
            return

        painter = QPainter(self)
        for val in self.splitValues:
            percent = val / self.maximum()
            px = percent * self.width()
            painter.drawLine(px, 0, px, 200)


class SplitWidget(QPushButton):

    def __init__(self, parent, splitId):
        super().__init__(parent)
        self.marked = False
        self.textOptions = ['✗', '✓']
        self.splitId = splitId
        self.toggleMark()

    def toggleMark(self):
        self.marked ^= True
        newText = self.textOptions[int(self.marked)]
        self.setText(newText)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        rightMerge, leftMerge = object(), object()
        if self.splitId < self.parent().splitsLayout.count() - 1:
            rightMerge = menu.addAction("Merge with right")
        if self.splitId > 0:
            leftMerge = menu.addAction("Merge with left")
        mark = menu.addAction("Unselect" if self.marked else "Select")
        edit = menu.addAction("Edit")
        save = menu.addAction("Save to file")
        action = menu.exec_(self.mapToGlobal(event.pos()))
        if action == rightMerge:
            self.parent().videoEditor.merge_split_with_next(self.splitId)
            self.parent().updateSplitsGUI()
        elif action == leftMerge:
            self.parent().videoEditor.merge_split_with_previous(self.splitId)
            self.parent().updateSplitsGUI()
        if action == save:
            videoExtension = self.parent().videoPath.split(".")[-1]
            fileName, _ = QFileDialog.getSaveFileName(self, "Choose video file", ".",
                                                      "Video Files (*.{})".format(videoExtension))
            if fileName:
                t = threading.Thread(target=self.exportSplit, args=(fileName, ))
                t.setDaemon(True)
                t.start()

        elif action == mark:
            self.toggleMark()
        elif action == edit:
            self.parent().openEditWindow(self.splitId)

    def exportSplit(self, filename):
        self.setDisabled(True)
        self.setText('⌛')
        self.parent().videoEditor.export_split(self.splitId, filename)
        textStatus = self.textOptions[int(self.marked)]
        self.setText(textStatus)
        self.setDisabled(False)


class EditWidget(QDialog):

    def __init__(self, parent):
        super().__init__(parent, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

        self.setWindowTitle("Edit split")
        self.splitId = None

        # Reencode layout
        self.reencodeCheckbox = QCheckBox("Reencode")
        self.reencodeCheckbox.setToolTip("Check this option to have more accurate cuts and avoid black "
                                         "frames at the end and beginning of the split")

        reencodeLayout = QVBoxLayout()
        reencodeLayout.setContentsMargins(0, 0, 0, 0)
        reencodeLayout.addWidget(self.reencodeCheckbox)

        # Compress layout
        self.compressCheckbox = QCheckBox("Compress")
        self.compressCheckbox.setToolTip("Check this option to compress video and audio quality "
                                         "and reduce the output file size")

        compressLayout = QVBoxLayout()
        compressLayout.setContentsMargins(0, 0, 0, 0)
        compressLayout.addWidget(self.compressCheckbox)

        # Audio layout
        self.removeAudioCheckbox = QCheckBox("Remove audio")
        self.removeAudioCheckbox.setToolTip("Check this option to delete audio")

        audioLayout = QVBoxLayout()
        audioLayout.setContentsMargins(0, 0, 0, 0)
        audioLayout.addWidget(self.removeAudioCheckbox)

        # Speedup layout
        self.speedupCheckbox = QCheckBox("Speed up/down")
        self.speedupCheckbox.setToolTip("Accelerate or decelerate video and audio speed")

        speedupLayoutOpt1 = QHBoxLayout()
        self.speedupFactor = QDoubleSpinBox()
        self.speedupFactor.setValue(1)
        self.speedupFactor.setMinimum(0)
        factorLabel = QLabel("Factor:")
        factorLabel.setToolTip("Increase or decrease video speed with this factor")
        speedupLayoutOpt1.addItem(QSpacerItem(25, 0, QSizePolicy.Minimum, QSizePolicy.Minimum))
        speedupLayoutOpt1.addWidget(factorLabel)
        speedupLayoutOpt1.addWidget(self.speedupFactor)

        speedupLayoutOpt2 = QHBoxLayout()
        self.keepFramesCheckbox = QCheckBox("Keep all frames")
        self.keepFramesCheckbox.setDisabled(True)
        speedupLayoutOpt2.addItem(QSpacerItem(25, 0, QSizePolicy.Minimum, QSizePolicy.Minimum))
        speedupLayoutOpt2.addWidget(self.keepFramesCheckbox)

        speedupLayout = QVBoxLayout()
        speedupLayout.setContentsMargins(0, 0, 0, 0)
        speedupLayout.addWidget(self.speedupCheckbox)
        speedupLayout.addLayout(speedupLayoutOpt1)
        speedupLayout.addLayout(speedupLayoutOpt2)

        # General layout
        layout = QVBoxLayout()
        layout.addLayout(reencodeLayout)
        layout.addLayout(compressLayout)
        layout.addLayout(audioLayout)
        layout.addLayout(speedupLayout)
        self.setLayout(layout)

    def updateFields(self, splitId, config):
        self.splitId = splitId
        self.reencodeCheckbox.setChecked(config.get('reencode', False))
        self.compressCheckbox.setChecked(config.get('compress', False))
        self.removeAudioCheckbox.setChecked(config.get('removeaudio', False))
        speedupSettings = config.get('speedup')
        if speedupSettings:
            self.speedupCheckbox.setChecked(True)
            self.speedupFactor.setValue(config['speedup'].get('factor', 1))
            self.keepFramesCheckbox.setChecked(not config['speedup'].get('dropframes', True))
        else:
            self.speedupCheckbox.setChecked(False)
            self.speedupFactor.setValue(1)
            self.keepFramesCheckbox.setChecked(False)

    def getSplitConfig(self):
        speedup = False
        if self.speedupCheckbox.isChecked():
            speedup = {
                'factor': self.speedupFactor.value(),
                'dropframes': not self.keepFramesCheckbox.isChecked(),
            }

        return {
            'reencode': self.reencodeCheckbox.isChecked(),
            'compress': self.compressCheckbox.isChecked(),
            'removeaudio': self.removeAudioCheckbox.isChecked(),
            'speedup': speedup
        }

    def saveConfig(self):
        config = self.getSplitConfig()
        self.parent().videoEditor.update_split(self.splitId, config)

    def reject(self):
        self.saveConfig()
        super().reject()


def open_interface():
    import sys

    def except_hook(cls, exception, traceback):
        sys.__excepthook__(cls, exception, traceback)

    sys.excepthook = except_hook

    app = QApplication(sys.argv)
    player = VideoPlayer()
    player.setWindowTitle("Simple Video Editor")
    player.resize(1000, 600)
    player.show()
    sys.exit(app.exec_())
