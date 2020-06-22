import sys 
from PySide2.QtWidgets import (QMainWindow, QDial)
from PySide2.QtCore import Slot, Qt, QFile, QIODevice
from PySide2.QtUiTools import QUiLoader
from pythonosc import udp_client 
from argparse import ArgumentParser 
from pathlib import Path

UI_FILE_NAME = str(Path(__file__).parent / "ui/synth-controller.ui") # Qt Designer ui file TODO fix path!
OSC_PORT = 1121

class Controller(QMainWindow):

    def __init__(self, parent = None):
        QMainWindow.__init__(self)

        self.load_view()
        self.load_client()

        for dial in self.central_widget.findChildren(QDial):
                dial.valueChanged.connect(self.dial_change)

        self.setWindowTitle("Wavetable Controller")
        self.setCentralWidget(self.central_widget)

        self.show()

    def dial_change(self, value):
        #pass
        #print(self.sender().objectName())
        self.client.send_message("/{}".format(self.sender().objectName()), int(value))

    def load_client(self):
        #Setting up network things
        self.parser = ArgumentParser()
        self.parser.add_argument("--ip", default="127.0.0.1")
        self.parser.add_argument("--port", default=OSC_PORT)
        args = self.parser.parse_args()
        #UDP client
        self.client = udp_client.SimpleUDPClient(args.ip, args.port)

    def load_view(self):
        self.ui_file = QFile(UI_FILE_NAME)
        if not self.ui_file.open(QIODevice.ReadOnly):
            print("Cannot open {}: {}".format(UI_FILE_NAME, self.ui_file.errorString()))
            sys.exit(-1)

        self.loader = QUiLoader()
        self.central_widget = self.loader.load(self.ui_file)
        self.ui_file.close()

        if not self.central_widget:
            print(self.loader.errorString())
            sys.exit(-1)