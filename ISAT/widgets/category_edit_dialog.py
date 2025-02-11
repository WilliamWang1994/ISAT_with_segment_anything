# -*- coding: utf-8 -*-
# @Author  : LG

from PyQt5 import QtWidgets, QtGui, QtCore
from ISAT.ui.category_choice import Ui_Dialog


class CategoryEditDialog(QtWidgets.QDialog, Ui_Dialog):
    """分类编辑对话框类，用于编辑已有标注的属性"""
    def __init__(self, parent, mainwindow, scene):
        """初始化分类编辑对话框
        
        Args:
            parent: 父窗口
            mainwindow: 主窗口对象
            scene: 场景对象
        """
        super(CategoryEditDialog, self).__init__(parent)

        self.setupUi(self)
        self.mainwindow = mainwindow
        self.scene = scene
        self.polygon = None  # 当前编辑的多边形对象

        # 连接信号和槽
        self.listWidget.itemClicked.connect(self.get_category)  # 类别列表点击事件
        self.pushButton_apply.clicked.connect(self.apply)       # 应用按钮点击事件
        self.pushButton_cancel.clicked.connect(self.cancel)     # 取消按钮点击事件

        # 设置为模态对话框
        self.setWindowModality(QtCore.Qt.WindowModality.WindowModal)

    def load_cfg(self):
        """加载配置，更新类别列表和当前多边形属性"""
        self.listWidget.clear()

        # 从配置文件获取标签列表
        labels = self.mainwindow.cfg.get('label', [])

        # 遍历标签列表，创建列表项
        for label in labels:
            name = label.get('name', 'UNKNOW')    # 类别名称
            color = label.get('color', '#000000')  # 类别颜色

            # 创建列表项和对应的部件
            item = QtWidgets.QListWidgetItem()
            item.setSizeHint(QtCore.QSize(200, 30))
            widget = QtWidgets.QWidget()

            # 创建水平布局
            layout = QtWidgets.QHBoxLayout()
            layout.setContentsMargins(9, 1, 9, 1)
            
            # 创建类别名称标签
            label_category = QtWidgets.QLabel()
            label_category.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            label_category.setText(name)
            label_category.setObjectName('label_category')

            # 创建颜色标签
            label_color = QtWidgets.QLabel()
            label_color.setFixedWidth(10)
            label_color.setStyleSheet("background-color: {};".format(color))
            label_color.setObjectName('label_color')

            # 添加部件到布局
            layout.addWidget(label_color)
            layout.addWidget(label_category)
            widget.setLayout(layout)

            # 添加到列表
            self.listWidget.addItem(item)
            self.listWidget.setItemWidget(item, widget)

            # 如果是当前多边形的类别，设置为选中状态
            if self.polygon is not None and self.polygon.category == name:
                self.listWidget.setCurrentItem(item)

        # 更新属性显示
        if self.polygon is None:
            # 清空所有属性
            self.spinBox_group.clear()
            self.lineEdit_category.clear()
            self.checkBox_iscrowded.setCheckState(False)
            self.lineEdit_note.clear()
            self.label_layer.setText('{}'.format(''))
        else:
            # 显示当前多边形的属性
            self.lineEdit_category.setText('{}'.format(self.polygon.category))
            self.lineEdit_category.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.spinBox_group.setValue(self.polygon.group)
            iscrowd = QtCore.Qt.CheckState.Checked if self.polygon.iscrowd == 1 else QtCore.Qt.CheckState.Unchecked
            self.checkBox_iscrowded.setCheckState(iscrowd)
            self.lineEdit_note.setText('{}'.format(self.polygon.note))
            self.label_layer.setText('{}'.format(self.polygon.zValue()))

        # 如果没有类别，显示警告
        if self.listWidget.count() == 0:
            QtWidgets.QMessageBox.warning(self, 'Warning', '请在标注前设置类别。')

    def get_category(self, item):
        """获取选中的类别名称并显示
        
        Args:
            item: 选中的列表项
        """
        widget = self.listWidget.itemWidget(item)
        label_category = widget.findChild(QtWidgets.QLabel, 'label_category')
        self.lineEdit_category.setText(label_category.text())
        self.lineEdit_category.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

    def apply(self):
        """应用修改，更新多边形属性"""
        # 获取输入的属性值
        category = self.lineEdit_category.text()
        group = self.spinBox_group.value()
        is_crowd = int(self.checkBox_iscrowded.isChecked())
        note = self.lineEdit_note.text()

        # 验证类别是否已选择
        if not category:
            QtWidgets.QMessageBox.warning(self, 'Warning', '请在提交前选择一个类别。')
            return

        # 更新多边形属性
        self.polygon.set_drawed(category, group, is_crowd, note,
                              QtGui.QColor(self.mainwindow.category_color_dict.get(category, '#000000')))
        # 更新标注列表显示
        # self.mainwindow.annos_dock_widget.update_listwidget()
        self.mainwindow.annos_dock_widget.listwidget_update_polygon(self.polygon)

        # 清除当前多边形引用并切换到查看模式
        self.polygon = None
        self.scene.change_mode_to_view()
        self.close()

    def cancel(self):
        """取消编辑，关闭对话框"""
        self.scene.cancel_draw()
        self.close()

    def closeEvent(self, a0: QtGui.QCloseEvent):
        """关闭事件处理"""
        self.cancel()

    def reject(self):
        """拒绝对话框时的处理"""
        self.cancel()
