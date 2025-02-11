# -*- coding: utf-8 -*-
# @Author  : LG
# from https://blog.51cto.com/u_15872074/5841477

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal, QTimer, QRect, QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen


class SwitchBtn(QWidget):
    """开关按钮组件类"""
    # 状态改变信号
    checkedChanged = pyqtSignal(bool)
    
    def __init__(self,parent=None):
        """初始化开关按钮"""
        super(QWidget, self).__init__(parent)

        # 开关状态
        self.checked = False
        # 关闭状态的背景颜色
        self.bgColorOff = QColor('#6E798A')
        # 打开状态的背景颜色
        self.bgColorOn = QColor('#70AEFF')

        # 滑块颜色（关闭状态）
        self.sliderColorOff = QColor(255, 255, 255)
        # 滑块颜色（打开状态）
        self.sliderColorOn = QColor(255, 255, 255)

        # 文字颜色（关闭状态）
        self.textColorOff = QColor(255, 255, 255)
        # 文字颜色（打开状态）
        self.textColorOn = QColor(255, 255, 255)

        # 关闭状态显示的文本
        self.textOff = "OFF"
        # 打开状态显示的文本
        self.textOn = "ON"

        # 滑块与边框的间距
        self.space = 2
        # 圆角矩形的半径
        self.rectRadius = 5

        # 滑块移动步长
        self.step = self.width() / 50
        # 滑块当前位置
        self.startX = 0
        # 滑块目标位置
        self.endX = 0

        # 初始化定时器用于动画
        self.timer = QTimer(self)
        # 定时器触发时更新滑块位置
        self.timer.timeout.connect(self.updateValue)
        # 设置字体
        self.setFont(QFont("timesnewroman", 10))

    def updateValue(self):
        """更新滑块位置，实现动画效果"""
        if self.checked:
            # 打开状态，向右移动
            if self.startX < self.endX:
                self.startX = self.startX + self.step
            else:
                self.startX = self.endX
                self.timer.stop()
        else:
            # 关闭状态，向左移动
            if self.startX  > self.endX:
                self.startX = self.startX - self.step
            else:
                self.startX = self.endX
                self.timer.stop()
        # 重绘组件
        self.update()

    def mousePressEvent(self,event):
        """鼠标点击事件处理"""
        # 切换开关状态
        self.checked = not self.checked
        # 发送状态改变信号
        self.checkedChanged.emit(self.checked)
        # 设置滑块移动步长
        self.step = self.width() / 20
        # 根据状态计算滑块目标位置
        if self.checked:
            self.endX = self.width() - self.height()
        else:
            self.endX = 0
        # 启动动画定时器
        self.timer.start(5)

    def paintEvent(self, evt):
        """绘制组件"""
        # 创建画笔并启用抗锯齿
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # 绘制背景
        self.drawBg(evt, painter)
        # 绘制滑块
        self.drawSlider(evt, painter)
        # 绘制文字
        self.drawText(evt, painter)
        painter.end()

    def drawText(self, event, painter):
        """绘制文字
        
        根据开关状态绘制ON/OFF文字
        """
        painter.save()
        if self.checked:
            painter.setPen(self.textColorOn)
            painter.drawText(0, 0, int(self.width() / 2 + self.space * 2), 
                           int(self.height()), Qt.AlignCenter, self.textOn)
        else:
            painter.setPen(self.textColorOff)
            painter.drawText(int(self.width() / 2), 0, 
                           int(self.width() / 2 - self.space), 
                           int(self.height()), Qt.AlignCenter, self.textOff)
        painter.restore()

    def drawBg(self, event, painter):
        """绘制背景
        
        绘制圆角矩形背景
        """
        painter.save()
        painter.setPen(Qt.NoPen)
        if self.checked:
            painter.setBrush(self.bgColorOn)
        else:
            painter.setBrush(self.bgColorOff)
        # 计算圆角半径
        radius = self.height() / 2
        # 圆的宽度等于高度
        circleWidth = self.height()

        # 创建圆角矩形路径
        path = QPainterPath()
        path.moveTo(radius, 0)
        path.arcTo(QRectF(0, 0, circleWidth, circleWidth), 90, 180)
        path.lineTo(self.width() - radius, self.height())
        path.arcTo(QRectF(self.width() - self.height(), 0, 
                         circleWidth, circleWidth), 270, 180)
        path.lineTo(radius, 0)

        painter.drawPath(path)
        painter.restore()

    def drawSlider(self, event, painter):
        """绘制滑块
        
        绘制圆形滑块
        """
        painter.save()
        if self.checked:
            painter.setBrush(self.sliderColorOn)
            painter.setPen(QPen(self.sliderColorOn, 1))
        else:
            painter.setBrush(self.sliderColorOff)

        # 计算滑块尺寸和位置
        sliderWidth = self.height() - self.space * 2
        sliderRect = QRectF(self.startX + self.space, self.space, 
                           sliderWidth, sliderWidth)
        # 绘制圆形滑块
        painter.drawEllipse(sliderRect)
        painter.restore()

    def setChecked(self, checked=False):
        """设置开关状态
        
        Args:
            checked: 是否选中
        """
        if self.checked != checked:
            self.mousePressEvent(None)
