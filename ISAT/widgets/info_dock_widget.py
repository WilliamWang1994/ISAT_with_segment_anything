# -*- coding: utf-8 -*-
# @Author  : LG

from PyQt5 import QtWidgets, QtCore, QtGui
from ISAT.ui.info_dock import Ui_Form

class InfoDockWidget(QtWidgets.QWidget, Ui_Form):
    def __init__(self, mainwindow):
        super(InfoDockWidget, self).__init__()
        self.setupUi(self)
        self.mainwindow = mainwindow
        self.Annotator.textChanged.connect(self.note_changed)
        self.Inspector.textChanged.connect(self.note_changed)

    def note_changed(self):
        if self.mainwindow.load_finished:
            self.mainwindow.set_saved_state(False)

    def update_widget(self):
        if self.mainwindow.current_label is not None:
            self.label_width.setText('{}'.format(self.mainwindow.current_label.width))
            self.label_height.setText('{}'.format(self.mainwindow.current_label.height))
            self.label_depth.setText('{}'.format(self.mainwindow.current_label.depth))
            self.json_state.setText('{}'.format(self.mainwindow.current_label.json_state))
            self.Annotator.setText(self.mainwindow.current_label.annotator)
            self.Inspector.setText(self.mainwindow.current_label.inspector)
            if self.mainwindow.current_label.annotator  != '':
                self.Annotator.setReadOnly(True)
            else:
                self.Annotator.setReadOnly(False)

            if self.mainwindow.current_label.inspector  != '':
                self.Inspector.setReadOnly(True)
            else:
                self.Inspector.setReadOnly(False)
