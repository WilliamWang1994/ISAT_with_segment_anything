# -*- coding: utf-8 -*-
# @Author  : LG
import hashlib
import json
import os
from PIL import Image
import numpy as np
from json import loads, dumps
from typing import List
from ISAT.loader.kmcrypt.encry import encry
from ISAT.loader.kmcrypt.decry import decry


class Object:
    def __init__(self, category:str, group:int, segmentation, area, layer, bbox, iscrowd=0, note=''):
        self.category = category
        self.group = group
        self.segmentation = segmentation
        self.area = area
        self.layer = layer
        self.bbox = bbox
        self.iscrowd = iscrowd
        self.note = note


class Annotation:
    def __init__(self, image_path, label_path):
        img_folder, img_name = os.path.split(image_path)
        self.description = 'ISAT'
        self.KEY = "@mark"
        self.SALT = "@@kingmed20250522@@"
        self.img_folder = img_folder
        self.img_name = img_name
        self.label_path = label_path
        self.annotator = ''
        self.inspector = ''
        self.json_state = 'OK'

        image = np.array(Image.open(image_path))
        if image.ndim == 3:
            self.height, self.width, self.depth = image.shape
        elif image.ndim == 2:
            self.height, self.width = image.shape
            self.depth = 0
        else:
            self.height, self.width, self.depth = image.shape[:, :3]
            print('Warning: Except image has 2 or 3 ndim, but get {}.'.format(image.ndim))
        del image

        self.objects:List[Object,...] = []

    def load_annotation(self):
        if os.path.exists(self.label_path):
            file_format = 'cry'
            with open(self.label_path, 'rb') as f:
                data = f.read()
                try:
                    out_data, data_len = decry(data, '', '')
                    dataset = loads(out_data[:data_len].decode("utf-8"))
                except:
                    try:
                        dataset = loads(data)
                        file_format = 'json'
                    except Exception as e:
                        print('read json error')
                        print(e)
                result, save_mark, computed_mark = self.check_mark(dataset, self.SALT, self.KEY)
                if not result:
                    self.json_state = '标注文件存在问题，请联系管理员'
                    return self
                info = dataset.get('info', {})
                description = info.get('description', '')
                if description == 'ISAT':
                    # ISAT格式json
                    objects = dataset.get('objects', [])
                    self.img_name = info.get('name', '')
                    width = info.get('width', None)
                    if width is not None:
                        self.width = width
                    height = info.get('height', None)
                    if height is not None:
                        self.height = height
                    depth = info.get('depth', None)
                    if depth is not None:
                        self.depth = depth
                    # self.note = info.get('note', '')
                    self.annotator = info.get('annotator', '')
                    self.inspector = info.get('inspector', '')

                    for obj in objects:
                        category = obj.get('category', 'unknow')
                        group = obj.get('group', 0)
                        if group is None: group = 0
                        segmentation = obj.get('segmentation', [])
                        iscrowd = obj.get('iscrowd', 0)
                        note = obj.get('note', '')
                        area = obj.get('area', 0)
                        layer = obj.get('layer', 2)
                        bbox = obj.get('bbox', [])
                        obj = Object(category, group, segmentation, area, layer, bbox, iscrowd, note)
                        self.objects.append(obj)
                else:
                    # 不再支持直接打开labelme标注文件（在菜单栏-tool-convert中提供了isat<->labelme相互转换工具）
                    print('Warning: The file {} is not a ISAT json.'.format(self.label_path))
            if file_format == 'json':
                self.save_annotation()
        return self

    def save_annotation(self):
        if self.json_state != 'OK':
            print('Warning: The json file {} is modified, please contact monitor.'.format(self.label_path))
            return False
        dataset = {}
        dataset['info'] = {}
        dataset['info']['description'] = self.description
        dataset['info']['folder'] = self.img_folder
        dataset['info']['name'] = self.img_name
        dataset['info']['width'] = self.width
        dataset['info']['height'] = self.height
        dataset['info']['depth'] = self.depth
        dataset['info']['annotator'] = self.annotator
        dataset['info']['inspector'] = self.inspector
        dataset['objects'] = []
        for obj in self.objects:
            object = {}
            object['category'] = obj.category
            object['group'] = obj.group
            object['segmentation'] = obj.segmentation
            object['area'] = obj.area
            object['layer'] = obj.layer
            object['bbox'] = obj.bbox
            object['iscrowd'] = obj.iscrowd
            object['note'] = obj.note
            dataset['objects'].append(object)
        with open(self.label_path, 'wb') as f:
            a = dumps(self.add_mark(dataset, self.SALT, self.KEY), indent=4)
            magic, version, data_len, output_len, output = encry(a.encode("utf-8"), '', '')
            f.write(magic)
            f.write(version.to_bytes(4, byteorder='little'))
            f.write(data_len.to_bytes(4, 'little'))
            f.write(output_len.to_bytes(4, 'little'))
            f.write(output)

        return True

    @staticmethod
    def get_mark(js_data: dict, salt: str) -> str:
        js_str = json.dumps(js_data)
        md5 = hashlib.md5()
        md5.update(salt.encode("utf-8"))
        md5.update(js_str.encode("utf-8"))
        return md5.hexdigest()

    def add_mark(self, js_data: dict, salt: str, key: str) -> dict:
        '''
        info:
            给 js_data 这个 json 对象计算出在不包含摘要时的摘要值
        params:
            js_data[dict]: json 对象，可以包含 mark 摘要，也可以不包含
            salt[str]: 生成摘要时的盐
            key[str]: 摘要生成后存放在 js_data 中的 key， 只支持1级目录

        return [dict]: 包含摘要值的 json 对象
        '''
        result = js_data.copy()
        if key in result:
            del result[key]  # 删掉之前的mark

        result[key] = self.get_mark(result, salt)
        return result

    def check_mark(self, js_data: dict, salt: str, key: str):
        '''
        info:
            检查 js_data 这个 json 对象中存储的摘要值和不包含摘要时的摘要值是否一致
        params:
            js_data[dict]: json 对象，不包含摘要值则当成""处理
            salt[str]: 计算摘要时的盐
            key[str]: 摘要存放在 js_data 中的 key， 只支持1级目录

        return:
            result[bool]: 是否一致
            save_mark[str]: 存在js_data中的摘要值
            computed_mark[str]: 实际计算出来的摘要值
        '''
        save_mark = js_data.get(key, "")
        if save_mark != "":
            js_data_remove_mark = js_data.copy()
            del js_data_remove_mark[key]
        else:
            js_data_remove_mark = js_data

        computed_mark = self.get_mark(js_data_remove_mark, salt)

        return save_mark == computed_mark, save_mark, computed_mark