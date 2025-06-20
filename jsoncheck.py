import json
import hashlib
import os

def get_mark(js_data:dict, salt:str)->str:
    js_str = json.dumps(js_data)
    md5 = hashlib.md5()
    md5.update(salt.encode("utf-8"))
    md5.update(js_str.encode("utf-8"))
    return  md5.hexdigest()
    
def add_mark(js_data:dict, salt:str, key:str)->dict:
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
        del result[key] # 删掉之前的mark

    result[key] = get_mark(result,salt)
    return result

def check_mark(js_data:dict, salt:str, key:str):
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

    computed_mark = get_mark(js_data_remove_mark, salt)

    return save_mark == computed_mark, save_mark, computed_mark

def modified_add_mark2json(json_file:str):
    KEY = "@mark"
    SALT = "@@kingmed20250522@@"
    with open(json_file, "r") as f:
        json_data = json.load(f)
    with open(json_file,"w") as f:
        json_data_mark = add_mark(json_data,SALT,KEY)
        print(f"save_md5:{json_data_mark[KEY]}")
        json.dump(json_data_mark, f)

def rec_read(file_path, path_list):
    """递归读取文件夹下的所有json文件
    Args:
        file_path: 文件夹路径
        path_list: 存储json文件路径的列表
    """
    files = os.listdir(file_path)
    for file in files:
        file_d = f'{file_path}/{file}'
        if os.path.isdir(file_d):
            rec_read(file_d, path_list)
        else:
            if 'json' in file_d:
                path_list.append(file_d)

def batch_add_mark2json(json_file_dir:str):
    file_list = []
    rec_read(json_file_dir, file_list)
    for json_file in file_list:
        if json_file.endswith(".json"):
            try:
                modified_add_mark2json(json_file)
            except:
                print(f"{json_file} error")


if __name__ == "__main__":
    # batch_add_mark2json("D:/PycharmProjects/data_annotation/Pancreatic")
    modified_add_mark2json("D:/追踪数据/gap_test/src/RX2023405002-P2/L-0426.json")
    # KEY = "@mark"
    # SALT = "@@kingmed20250522@@"
    # with open("test_src.json","r") as f:
    #     json_data = json.load(f)
    #     result, save_mark, computed_mark = check_mark(json_data, SALT, KEY)
    #     print(f"{result=}, {save_mark=}, {computed_mark=}")
    #
    # with open("./test.json","w") as f:
    #     json_data_mark = add_mark(json_data,SALT,KEY)
    #     print(f"save_md5:{json_data_mark[KEY]}")
    #     json.dump(json_data_mark, f)



    


