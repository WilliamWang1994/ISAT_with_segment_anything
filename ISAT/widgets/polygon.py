# -*- coding: utf-8 -*-
# @Author  : LG
import time
from ctypes import c_voidp

import cv2
import numpy as np
from PyQt5 import QtCore, QtWidgets, QtGui
from ISAT.annotation import Object
import typing
from ISAT.configs import STATUSMode, CLICKMode, DRAWMode, CONTOURMode


class PromptPoint(QtWidgets.QGraphicsPathItem):
    def __init__(self, pos, type=0):
        super(PromptPoint, self).__init__()
        self.color = QtGui.QColor('#0000FF') if type==0 else QtGui.QColor('#00FF00')
        self.color.setAlpha(255)
        self.painterpath = QtGui.QPainterPath()
        self.painterpath.addEllipse(
            QtCore.QRectF(-1, -1, 2, 2))
        self.setPath(self.painterpath)
        # 设置填充颜色
        self.setBrush(self.color)
        # 设置边框颜色和宽度(3像素)
        self.setPen(QtGui.QPen(self.color, 3))
        self.setZValue(1e5)

        self.setPos(pos)


class Vertex(QtWidgets.QGraphicsPathItem):
    def __init__(self, polygon, color, nohover_size=2):
        super(Vertex, self).__init__()
        self.polygon = polygon
        self.color = color
        self.color.setAlpha(255)
        self.nohover_size = nohover_size
        self.hover_size = self.nohover_size + 2
        self.line_width = 0

        self.nohover = QtGui.QPainterPath()
        self.nohover.addEllipse(QtCore.QRectF(-self.nohover_size//2, -self.nohover_size//2, self.nohover_size, self.nohover_size))
        self.hover = QtGui.QPainterPath()
        self.hover.addRect(QtCore.QRectF(-self.nohover_size//2, -self.nohover_size//2, self.nohover_size, self.nohover_size))

        self.setPath(self.nohover)
        self.setBrush(self.color)
        self.setPen(QtGui.QPen(self.color, self.line_width))
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(1e5)

    def setColor(self, color):
        self.color = QtGui.QColor(color)
        self.color.setAlpha(255)
        self.setPen(QtGui.QPen(self.color, self.line_width))
        self.setBrush(self.color)

    def itemChange(self, change: 'QtWidgets.QGraphicsItem.GraphicsItemChange', value: typing.Any):
        if change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.scene().mainwindow.actionDelete.setEnabled(self.isSelected())
            if self.isSelected():
                selected_color = QtGui.QColor('#00A0FF')
                self.setBrush(selected_color)
            else:
                self.setBrush(self.color)

        if change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.isEnabled():
            # 限制顶点移动到图外
            if value.x() < 0:
                value.setX(0)
            if value.x() > self.scene().width()-1:
                value.setX(self.scene().width()-1)
            if value.y() < 0:
                value.setY(0)
            if value.y() > self.scene().height()-1:
                value.setY(self.scene().height()-1)
            index = self.polygon.vertexs.index(self)
            self.polygon.movePoint(index, value)

        return super(Vertex, self).itemChange(change, value)
    
    def hoverEnterEvent(self, event: 'QGraphicsSceneHoverEvent'):
        self.scene().hovered_vertex = self
        if self.scene().mode == STATUSMode.CREATE: # CREATE
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.CrossCursor))
        else: # EDIT, VIEW
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.OpenHandCursor))
            if not self.isSelected():
                self.setBrush(QtGui.QColor(255, 255, 255, 255))
            self.setPath(self.hover)
        super(Vertex, self).hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent'):
        self.scene().hovered_vertex = None
        if not self.isSelected():
            self.setBrush(self.color)
        self.setPath(self.nohover)
        super(Vertex, self).hoverLeaveEvent(event)


class Polygon(QtWidgets.QGraphicsPolygonItem):
    def __init__(self):
        super(Polygon, self).__init__(parent=None)
        self.line_width = 1
        self.hover_alpha = 150
        self.nohover_alpha = 80
        self.points = []
        self.vertexs = []
        self.category = ''
        self.group = 0
        self.iscrowd = 0
        self.note = ''

        self.rxmin, self.rxmax, self.rymin, self.rymax = 0, 0, 0, 0 # 用于绘画完成后，记录多边形的各边界，此处与points对应
        self.color = QtGui.QColor('#ff0000')
        self.is_drawing = True

        self.setPen(QtGui.QPen(self.color, self.line_width))
        self.setBrush(QtGui.QBrush(self.color, QtCore.Qt.BrushStyle.FDiagPattern))

        self.setAcceptHoverEvents(True)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setZValue(1e5)

    def addPoint(self, point):
        self.points.append(point)
        vertex = Vertex(self, self.color, self.scene().mainwindow.cfg['software']['vertex_size'] * 2)
        # 添加路径点
        self.scene().addItem(vertex)
        self.vertexs.append(vertex)
        vertex.setPos(point)

    def movePoint(self, index, point):
        if not 0 <= index < len(self.points):
            return
        self.points[index] = self.mapFromScene(point)

        self.redraw()
        if self.scene().mainwindow.load_finished and not self.is_drawing:
            self.scene().mainwindow.set_saved_state(False)

    def removePoint(self, index):
        if not self.points:
            return
        self.points.pop(index)
        vertex = self.vertexs.pop(index)
        self.scene().removeItem(vertex)
        del vertex
        self.redraw()

    def delete(self):
        self.points.clear()
        while self.vertexs:
            vertex = self.vertexs.pop()
            self.scene().removeItem(vertex)
            del vertex

    def moveVertex(self, index, point):
        if not 0 <= index < len(self.vertexs):
            return
        vertex = self.vertexs[index]
        vertex.setEnabled(False)
        vertex.setPos(point)
        vertex.setEnabled(True)

    def itemChange(self, change: 'QGraphicsItem.GraphicsItemChange', value: typing.Any):
        if (change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged
                and not self.is_drawing
                and self.scene().mode!=STATUSMode.CREATE): # 选中改变
            if self.isSelected():
                color = QtGui.QColor('#00A0FF')
                color.setAlpha(self.hover_alpha)
                self.setBrush(color)
                self.scene().selected_polygons_list.append(self)
            else:
                self.color.setAlpha(self.nohover_alpha)
                self.setBrush(self.color)
                if self in self.scene().selected_polygons_list:
                    self.scene().selected_polygons_list.remove(self)
            self.scene().mainwindow.annos_dock_widget.set_selected(self) # 更新label面板

        if change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionChange: # ItemPositionHasChanged
            bias = value
            l, t, b, r = self.boundingRect().left(), self.boundingRect().top(), self.boundingRect().bottom(), self.boundingRect().right()
            if l + bias.x() < 0: bias.setX(-l)
            if r + bias.x() > self.scene().width(): bias.setX(self.scene().width()-r)
            if t + bias.y() < 0: bias.setY(-t)
            if b + bias.y() > self.scene().height(): bias.setY(self.scene().height()-b)

            for index, point in enumerate(self.points):
                self.moveVertex(index, point+bias)

            if self.scene().mainwindow.load_finished and not self.is_drawing:
                self.scene().mainwindow.set_saved_state(False)

        if change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            value = 0 if self.is_drawing else value
        if change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged and self.isSelected():
            self.setSelected(not self.is_drawing)
        return super(Polygon, self).itemChange(change, value)

    def hoverEnterEvent(self, event: 'QGraphicsSceneHoverEvent'):
        if not self.is_drawing and not self.isSelected():
            self.color.setAlpha(self.hover_alpha)
            self.setBrush(self.color)
        super(Polygon, self).hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent'):
        if not self.is_drawing and not self.isSelected():
            self.color.setAlpha(self.nohover_alpha)
            self.setBrush(self.color)
        super(Polygon, self).hoverEnterEvent(event)

    def mouseDoubleClickEvent(self, event: 'QGraphicsSceneMouseEvent'):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.scene().mainwindow.category_edit_widget.polygon = self
            self.scene().mainwindow.category_edit_widget.load_cfg()
            self.scene().mainwindow.category_edit_widget.show()

    def redraw(self):
        if len(self.points) < 1:
            return
        xs = [p.x() for p in self.points]
        ys = [p.y() for p in self.points]
        self.rxmin, self.rymin, self.rxmax, self.rymax = min(xs), min(ys), max(xs), max(ys)
        self.setPolygon(QtGui.QPolygonF(self.points))

    def change_color(self, color):
        self.color = color
        if not self.scene().mainwindow.cfg['software']['show_edge']:
            color.setAlpha(0)
        self.setPen(QtGui.QPen(color, self.line_width))
        self.color.setAlpha(self.nohover_alpha)
        self.setBrush(self.color)
        for vertex in self.vertexs:
            vertex_color = self.color
            vertex_color.setAlpha(255)
            vertex.setPen(QtGui.QPen(vertex_color, self.line_width))
            vertex.setBrush(vertex_color)

    def set_drawed(self, category, group, iscrowd, note, color:QtGui.QColor, layer=None):
        self.is_drawing = False
        self.category = category
        if isinstance(group, str):
            group = 0 if group == '' else int(group)
        self.group = group
        self.iscrowd = iscrowd
        self.note = note

        self.color = color
        if not self.scene().mainwindow.cfg['software']['show_edge']:
            color.setAlpha(0)
        self.setPen(QtGui.QPen(color, self.line_width))
        self.color.setAlpha(self.nohover_alpha)
        self.setBrush(self.color)
        if layer is not None:
            self.setZValue(layer)
            for vertex in self.vertexs:
                vertex.setZValue(layer)
        for vertex in self.vertexs:
            vertex.setColor(color)

    def calculate_area_perimeter(self):
        area = 0
        perimeter = 0
        num_points = len(self.points)
        for i in range(num_points):
            p1 = self.points[i]
            p2 = self.points[(i + 1) % num_points]
            shoelace = p1.x() * p2.y() - p2.x() * p1.y()
            d = np.sqrt((p2.y() - p1.y())**2+(p2.x() - p1.x())**2)
            area += shoelace
            perimeter += d
        return abs(area) / 2, perimeter

    def calculate_major_minor_axis(self):
        temp_contour = []
        for i in range(len(self.points)):
            temp_contour.append([int(self.points[i].x()), int(self.points[i].y())])
        ellipse = cv2.fitEllipse(np.asarray(temp_contour))
        center, axes, angle = ellipse
        major_axis, minor_axis = axes
        # angle_rad = np.deg2rad(angle)
        # cos_angle = np.cos(angle_rad)
        # sin_angle = np.sin(angle_rad)

        # 长轴端点坐标
        # x1 = int(center[0] + major_axis / 2 * cos_angle)
        # y1 = int(center[1] - major_axis / 2 * sin_angle)
        # x2 = int(center[0] - major_axis / 2 * cos_angle)
        # y2 = int(center[1] + major_axis / 2 * sin_angle)
        # major_len = np.sqrt((y2-y1)**2+(x2-x1)**2)
        #
        # # 短轴端点坐标
        # x3 = int(center[0] + minor_axis / 2 * sin_angle)
        # y3 = int(center[1] + minor_axis / 2 * cos_angle)
        # x4 = int(center[0] - minor_axis / 2 * sin_angle)
        # y4 = int(center[1] - minor_axis / 2 * cos_angle)
        # minor_len = np.sqrt((y4 - y3) ** 2 + (x4 - x3) ** 2)

        return [major_axis, minor_axis] if major_axis > minor_axis else [minor_axis, major_axis]

    def load_object(self, object):
        segmentation = object.segmentation
        for x, y in segmentation:
            point = QtCore.QPointF(x, y)
            self.addPoint(point)
        color = self.scene().mainwindow.category_color_dict.get(object.category, '#000000')
        self.set_drawed(object.category, object.group, object.iscrowd, object.note, QtGui.QColor(color), object.layer)  # ...

    def to_object(self):
        if self.is_drawing:
            return None
        segmentation = []
        for point in self.points:
            point = point + self.pos()
            segmentation.append((round(point.x(), 2), round(point.y(), 2)))
        xmin = self.boundingRect().x() + self.pos().x()
        ymin = self.boundingRect().y() + self.pos().y()
        xmax = xmin + self.boundingRect().width()
        ymax = ymin + self.boundingRect().height()

        object = Object(self.category, group=self.group, segmentation=segmentation,
                        area=self.calculate_area_perimeter()[0], layer=self.zValue(), bbox=(xmin, ymin, xmax, ymax), iscrowd=self.iscrowd, note=self.note)
        return object


class LineVertex(QtWidgets.QGraphicsPathItem):
    def __init__(self, polygon, color, nohover_size=2):
        super(LineVertex, self).__init__()
        self.polygon = polygon
        self.color = color
        self.color.setAlpha(255)
        self.nohover_size = nohover_size
        self.hover_size = self.nohover_size + 2
        self.line_width = 0

        self.nohover = QtGui.QPainterPath()
        self.nohover.addEllipse(QtCore.QRectF(-self.nohover_size//2, -self.nohover_size//2, self.nohover_size, self.nohover_size))
        self.hover = QtGui.QPainterPath()
        self.hover.addRect(QtCore.QRectF(-self.nohover_size//2, -self.nohover_size//2, self.nohover_size, self.nohover_size))

        self.setPath(self.nohover)
        self.setBrush(self.color)
        self.setPen(QtGui.QPen(self.color, self.line_width))
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(1e5)

    def itemChange(self, change: 'QtWidgets.QGraphicsItem.GraphicsItemChange', value: typing.Any):
        if change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.scene().mainwindow.actionDelete.setEnabled(self.isSelected())
            if self.isSelected():
                selected_color = QtGui.QColor('#00A0FF')
                self.setBrush(selected_color)
            else:
                self.setBrush(self.color)

        if change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.isEnabled():
            # 限制顶点移动到图外
            if value.x() < 0:
                value.setX(0)
            if value.x() > self.scene().width()-1:
                value.setX(self.scene().width()-1)
            if value.y() < 0:
                value.setY(0)
            if value.y() > self.scene().height()-1:
                value.setY(self.scene().height()-1)
            index = self.polygon.vertexs.index(self)
            self.polygon.movePoint(index, value)

        return super(LineVertex, self).itemChange(change, value)


class Line(QtWidgets.QGraphicsPathItem):
    def __init__(self):
        super().__init__(parent=None)
        self.line_width = 1
        # self.hover_alpha = 150
        # self.nohover_alpha = 80
        self.points = []
        self.vertexs = []
        self.color = QtGui.QColor('#ff0000')

    def addPoint(self, point):
        self.points.append(point)
        vertex = LineVertex(self, self.color, self.scene().mainwindow.cfg['software']['vertex_size'] * 2)
        # 添加路径点
        self.scene().addItem(vertex)
        self.vertexs.append(vertex)
        vertex.setPos(point)

    def movePoint(self, index, point):
        if not 0 <= index < len(self.points):
            return
        self.points[index] = self.mapFromScene(point)
        self.redraw()

    def removePoint(self, index):
        if not self.points:
            return
        self.points.pop(index)
        vertex = self.vertexs.pop(index)
        self.scene().removeItem(vertex)
        del vertex
        self.redraw()

    def delete(self):
        self.points.clear()
        while self.vertexs:
            vertex = self.vertexs.pop()
            self.scene().removeItem(vertex)
            del vertex

    def redraw(self):
        if len(self.points) < 1:
            return
        xs = [p.x() for p in self.points]
        ys = [p.y() for p in self.points]
        self.rxmin, self.rymin, self.rxmax, self.rymax = min(xs), min(ys), max(xs), max(ys)

        line_path = QtGui.QPainterPath()
        if self.points:
            line_path.moveTo(self.points[0])
            for point in self.points[1:]:
                line_path.lineTo(point)

        self.setPath(line_path)


class RectVertex(QtWidgets.QGraphicsPathItem):
    def __init__(self, rect, color, nohover_size=2):
        super(RectVertex, self).__init__()
        self.rect = rect
        self.color = color
        self.color.setAlpha(255)
        self.nohover_size = nohover_size
        self.hover_size = self.nohover_size + 2
        self.line_width = 0

        self.nohover = QtGui.QPainterPath()
        self.nohover.addEllipse(QtCore.QRectF(-self.nohover_size//2, -self.nohover_size//2, self.nohover_size, self.nohover_size))
        self.hover = QtGui.QPainterPath()
        self.hover.addRect(QtCore.QRectF(-self.nohover_size//2, -self.nohover_size//2, self.nohover_size, self.nohover_size))

        self.setPath(self.nohover)
        self.setBrush(self.color)
        self.setPen(QtGui.QPen(self.color, self.line_width))
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(1e5)

    def itemChange(self, change: 'QtWidgets.QGraphicsItem.GraphicsItemChange', value: typing.Any):
        if change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.scene().mainwindow.actionDelete.setEnabled(self.isSelected())
            if self.isSelected():
                selected_color = QtGui.QColor('#00A0FF')
                self.setBrush(selected_color)
            else:
                self.setBrush(self.color)

        if change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.isEnabled():
            # 限制顶点移动到图外
            if value.x() < 0:
                value.setX(0)
            if value.x() > self.scene().width()-1:
                value.setX(self.scene().width()-1)
            if value.y() < 0:
                value.setY(0)
            if value.y() > self.scene().height()-1:
                value.setY(self.scene().height()-1)
            index = self.rect.vertexs.index(self)
            self.rect.movePoint(index, value)

        return super(RectVertex, self).itemChange(change, value)


class Rect(QtWidgets.QGraphicsRectItem):
    def __init__(self):
        super().__init__(parent=None)
        self.line_width = 1
        self.points = []
        self.vertexs = []
        self.color = QtGui.QColor('#ff0000')

    def addPoint(self, point):
        self.points.append(point)
        vertex = RectVertex(self, self.color, self.scene().mainwindow.cfg['software']['vertex_size'] * 2)
        # 添加路径点
        self.scene().addItem(vertex)
        self.vertexs.append(vertex)
        vertex.setPos(point)

    def movePoint(self, index, point):
        if not 0 <= index < len(self.points):
            return
        self.points[index] = self.mapFromScene(point)
        self.redraw()

    def removePoint(self, index):
        if not self.points:
            return
        self.points.pop(index)
        vertex = self.vertexs.pop(index)
        self.scene().removeItem(vertex)
        del vertex
        self.redraw()

    def delete(self):
        self.points.clear()
        while self.vertexs:
            vertex = self.vertexs.pop()
            self.scene().removeItem(vertex)
            del vertex

    def redraw(self):
        if len(self.points) < 2:
            return

        self.setRect(QtCore.QRectF(self.points[0], self.points[-1]))


class BlurRect(QtWidgets.QGraphicsRectItem):
    def __init__(self):
        super(BlurRect, self).__init__(parent=None)
        self.line_width = 1
        self.hover_alpha = 150
        self.nohover_alpha = 80
        self.points = []
        self.vertexs = []
        self.category = ''
        self.group = 0
        self.iscrowd = 0
        self.note = ''
        self.press = False
        self.rxmin, self.rxmax, self.rymin, self.rymax = 0, 0, 0, 0 # 用于绘画完成后，记录多边形的各边界，此处与points对应
        self.color = QtGui.QColor('#ff0000')
        self.is_drawing = True

        self.setPen(QtGui.QPen(self.color, self.line_width))
        self.text_item = QtWidgets.QGraphicsTextItem()
        # 设置Z值
        self.text_item.setZValue(1e5)
        # self.setBrush(QtGui.QBrush(self.color, QtCore.Qt.BrushStyle.FDiagPattern))

        self.setAcceptHoverEvents(True)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setZValue(1e5)

    def addPoint(self, point):
        if len(self.points) <3:
            self.points.append(point)
            vertex = Vertex(self, self.color, self.scene().mainwindow.cfg['software']['vertex_size'] * 2)
            # 添加路径点
            self.scene().addItem(vertex)
            self.vertexs.append(vertex)
            vertex.setPos(point)
        else:
            self.points.pop()
            temp_ver = self.vertexs.pop()
            self.scene().removeItem(temp_ver)

            self.points.append(point)
            vertex = Vertex(self, self.color, self.scene().mainwindow.cfg['software']['vertex_size'] * 2)
            # 添加路径点
            self.scene().addItem(vertex)
            self.vertexs.append(vertex)
            vertex.setPos(point)

    def movePoint(self, index, point):
        if not 0 <= index < len(self.points):
            return
        if len(self.points) > 1:
            self.points[index] = self.mapFromScene(point)
        else:
            self.points.append(self.mapFromScene(point))

        self.redraw()
        if self.scene().mainwindow.load_finished and not self.is_drawing:
            self.scene().mainwindow.set_saved_state(False)

    def removePoint(self, index):
        if not self.points:
            return
        self.points.pop(index)
        vertex = self.vertexs.pop(index)
        self.scene().removeItem(vertex)
        del vertex
        self.redraw()

    def determine_blur(self,image):
        xs = [p.x() for p in self.points]
        ys = [p.y() for p in self.points]
        self.rxmin, self.rymin, self.rxmax, self.rymax = int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))
        part_image = image[self.rymin:self.rymax, self.rxmin:self.rxmax]
        gray = cv2.cvtColor(part_image, cv2.COLOR_RGB2GRAY)
        fm = cv2.Laplacian(gray, cv2.CV_64F).var()
        w = self.rxmax - self.rxmin
        print(f'模糊度：{fm}')
        self.text_item.setFont(QtGui.QFont("Arial", 10))
        if fm < self.scene().mainwindow.cfg['software']['blur_th']:
            self.text_item.setPlainText('blurry')
            self.text_item.setDefaultTextColor(self.color)
            # 设置字体

        else:
            self.text_item.setPlainText('clear')
            self.text_item.setDefaultTextColor(QtGui.QColor('green'))
            # 设置字体


        # item0.setPlainText('this is plain text')
        self.text_item.setPos(self.rxmin, self.rymin-20)
        self.scene().addItem(self.text_item)

        # self.scene().update()
        # time.sleep(3)
        # self.scene().removeItem(self.text_item)
        # return fm


    def delete(self):
        self.points.clear()
        while self.vertexs:
            vertex = self.vertexs.pop()
            self.scene().removeItem(vertex)
            del vertex
        self.scene().removeItem(self.text_item)

    # def moveVertex(self, index, point):
    #     if not 0 <= index < len(self.vertexs):
    #         return
    #     vertex = self.vertexs[index]
    #     vertex.setEnabled(False)
    #     vertex.setPos(point)
    #     vertex.setEnabled(True)

    def itemChange(self, change: 'QGraphicsItem.GraphicsItemChange', value: typing.Any):
        if (change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged
                and not self.is_drawing
                and self.scene().mode!=STATUSMode.CREATE): # 选中改变
            if self.isSelected():
                color = QtGui.QColor('#00A0FF')
                color.setAlpha(self.hover_alpha)
                self.setBrush(color)
                self.scene().selected_polygons_list.append(self)
            else:
                self.color.setAlpha(self.nohover_alpha)
                self.setBrush(self.color)
                if self in self.scene().selected_polygons_list:
                    self.scene().selected_polygons_list.remove(self)
            self.scene().mainwindow.annos_dock_widget.set_selected(self) # 更新label面板

        if change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionChange: # ItemPositionHasChanged
            bias = value
            l, t, b, r = self.boundingRect().left(), self.boundingRect().top(), self.boundingRect().bottom(), self.boundingRect().right()
            if l + bias.x() < 0: bias.setX(-l)
            if r + bias.x() > self.scene().width(): bias.setX(self.scene().width()-r)
            if t + bias.y() < 0: bias.setY(-t)
            if b + bias.y() > self.scene().height(): bias.setY(self.scene().height()-b)

            for index, point in enumerate(self.points):
                self.moveVertex(index, point+bias)

            if self.scene().mainwindow.load_finished and not self.is_drawing:
                self.scene().mainwindow.set_saved_state(False)

        if change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            value = 0 if self.is_drawing else value
        if change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged and self.isSelected():
            self.setSelected(not self.is_drawing)
        return super(BlurRect, self).itemChange(change, value)

    def hoverEnterEvent(self, event: 'QGraphicsSceneHoverEvent'):
        if not self.is_drawing and not self.isSelected():
            self.color.setAlpha(self.hover_alpha)
            self.setBrush(self.color)
        super(BlurRect, self).hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent'):
        if not self.is_drawing and not self.isSelected():
            self.color.setAlpha(self.nohover_alpha)
            self.setBrush(self.color)
        super(BlurRect, self).hoverEnterEvent(event)

    # def mouseDoubleClickEvent(self, event: 'QGraphicsSceneMouseEvent'):
    #     if event.button() == QtCore.Qt.MouseButton.LeftButton:
    #         self.scene().mainwindow.category_edit_widget.polygon = self
    #         self.scene().mainwindow.category_edit_widget.load_cfg()
    #         self.scene().mainwindow.category_edit_widget.show()

    def redraw(self):
        if len(self.points) < 1:
            return
        xs = [p.x() for p in self.points]
        ys = [p.y() for p in self.points]
        self.rxmin, self.rymin, self.rxmax, self.rymax = min(xs), min(ys), max(xs), max(ys)
        w = self.rxmax - self.rxmin
        h = self.rymax - self.rymin
        self.setRect(QtCore.QRectF(self.rxmin, self.rymin, w, h))

    # def change_color(self, color):
    #     self.color = color
    #     if not self.scene().mainwindow.cfg['software']['show_edge']:
    #         color.setAlpha(0)
    #     self.setPen(QtGui.QPen(color, self.line_width))
    #     self.color.setAlpha(self.nohover_alpha)
    #     self.setBrush(self.color)
    #     for vertex in self.vertexs:
    #         vertex_color = self.color
    #         vertex_color.setAlpha(255)
    #         vertex.setPen(QtGui.QPen(vertex_color, self.line_width))
    #         vertex.setBrush(vertex_color)
    #
    # def set_drawed(self, category, group, iscrowd, note, color:QtGui.QColor, layer=None):
    #     self.is_drawing = False
    #     self.category = category
    #     if isinstance(group, str):
    #         group = 0 if group == '' else int(group)
    #     self.group = group
    #     self.iscrowd = iscrowd
    #     self.note = note
    #
    #     self.color = color
    #     if not self.scene().mainwindow.cfg['software']['show_edge']:
    #         color.setAlpha(0)
    #     self.setPen(QtGui.QPen(color, self.line_width))
    #     self.color.setAlpha(self.nohover_alpha)
    #     self.setBrush(self.color)
    #     if layer is not None:
    #         self.setZValue(layer)
    #         for vertex in self.vertexs:
    #             vertex.setZValue(layer)
    #     for vertex in self.vertexs:
    #         vertex.setColor(color)
    #
    # def calculate_area_perimeter(self):
    #     area = 0
    #     perimeter = 0
    #     num_points = len(self.points)
    #     for i in range(num_points):
    #         p1 = self.points[i]
    #         p2 = self.points[(i + 1) % num_points]
    #         shoelace = p1.x() * p2.y() - p2.x() * p1.y()
    #         d = np.sqrt((p2.y() - p1.y())**2+(p2.x() - p1.x())**2)
    #         area += shoelace
    #         perimeter += d
    #     return abs(area) / 2, perimeter
    #
    # def load_object(self, object):
    #     segmentation = object.segmentation
    #     for x, y in segmentation:
    #         point = QtCore.QPointF(x, y)
    #         self.addPoint(point)
    #     color = self.scene().mainwindow.category_color_dict.get(object.category, '#000000')
    #     self.set_drawed(object.category, object.group, object.iscrowd, object.note, QtGui.QColor(color), object.layer)  # ...
    #
    # def to_object(self):
    #     if self.is_drawing:
    #         return None
    #     segmentation = []
    #     for point in self.points:
    #         point = point + self.pos()
    #         segmentation.append((round(point.x(), 2), round(point.y(), 2)))
    #     xmin = self.boundingRect().x() + self.pos().x()
    #     ymin = self.boundingRect().y() + self.pos().y()
    #     xmax = xmin + self.boundingRect().width()
    #     ymax = ymin + self.boundingRect().height()
    #
    #     object = Object(self.category, group=self.group, segmentation=segmentation,
    #                     area=self.calculate_area_perimeter()[0], layer=self.zValue(), bbox=(xmin, ymin, xmax, ymax), iscrowd=self.iscrowd, note=self.note)
    #     return object