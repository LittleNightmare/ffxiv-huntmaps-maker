import csv
import json
import os

import yaml

import pandas as pd


# 所有csv可以分别在ffxiv-dataming找到，国际服增加后缀_en，国服不变

# 将marks.json 翻译成中文
def tran_marks():
    BNpcName_en = []
    BNpcName_cn = []
    with open("BNpcName_en.csv", encoding="utf8", mode="r") as f:
        csv_en = csv.reader(f)
        for x in csv_en:
            BNpcName_en.append(x[1].lower())

    with open("BNpcName.csv", encoding="utf8", mode="r") as f:
        csv_cn = csv.reader(f)
        for x in csv_cn:
            BNpcName_cn.append(x[1])

    table = {}
    for i in range(len(BNpcName_cn)):
        table[BNpcName_en[i]] = BNpcName_cn[i]

    with open("marks.json", encoding="utf8", mode="r") as f:
        marks_en = json.load(f)
        for k in marks_en:
            # print(table[k["name"]])
            try:
                # print(k["name"] + ": " + table[k["name"]])
                cn_name = table[k["name"].lower()]
                if cn_name != "":
                    k["name"] = cn_name
                else:
                    print(k["name"] + " not exist cn name")
            except KeyError as e:
                print("KeyError: " + str(e))
        with open("marks_cn.json", encoding="utf8", mode="w") as f:
            json.dump(marks_en, f, ensure_ascii=False, indent=4, sort_keys=True)


# 生成一个地名对照字典
def get_place_name(table_type_cnkey=False):
    # 读取 CSV 文件
    df_en = pd.read_csv("PlaceName_en.csv", encoding="utf8", header= 0, skiprows=[1, 2], usecols=[0, 1])
    df_cn = pd.read_csv("PlaceName.csv", encoding="utf8", header= 0, skiprows=[1, 2], usecols=[0, 1])

    df_en = df_en.dropna()
    df_cn = df_cn.dropna()

    # 合并两个 DataFrame
    df = pd.merge(df_en, df_cn, left_on='key', right_on='key', suffixes=('_en', '_cn'))

    # 生成字典，避免覆盖重复的键
    table = {}
    if table_type_cnkey:
        for cn, en in zip(df['0_cn'], df['0_en']):
            if cn not in table:
                table[cn] = en
    else:
        for en, cn in zip(df['0_en'], df['0_cn']):
            if en not in table:
                table[en] = cn

    return table


# 原本打算修改zone_info但要改的太多，放弃了，现在就是输出个区域名字对照
def tran_zone_info():
    table = get_place_name()

    with open("zone_info.yaml", encoding="utf8", mode="r") as f:
        zone_info = yaml.load(f, Loader=yaml.Loader)
        for zone in zone_info.items():
            print(table[zone[0]] + ":" + zone[0])
            zone[1]["region"] = table[zone[1]["region"]]
            temp = table[zone[0]]
            zone = (temp, zone[1])
            # print(zone)
            # zone[0] = table[zone[0]]
            # print(table[zone[1]["region"]])
            # print(table[zone[0]])
        # print(zone_info)
        # with open("zone_info_cn.yaml", encoding="utf8", mode="w") as f:
        #     yaml.dump(zone_info, f)


# 将输出的地图，从英文文件夹名字转换到中文
def rename_map(root, from_cn_to_en):
    # 这里可以控制中文转英文或相反,True 中转英
    table = get_place_name(from_cn_to_en)
    dirs = os.listdir(root)
    for dir in dirs:
        current = os.path.join(root, dir)
        if os.path.isdir(current):
            rename_map(current, from_cn_to_en)
            try:
                if "0" in dir:
                    place, num = dir.split(" 0")
                    new_path = os.path.join(root, table[place] + " 0" + num)
                    print("new: " + new_path)
                    os.rename(current, new_path)
                else:
                    new_path = os.path.join(root, table[dir])
                    print("new: " + new_path)
                    os.rename(current, new_path)
            except KeyError as e:
                print("old: " + current)


# 基于zone_info.yaml生成地图列表
def get_map_list_from_zone_info():
    with open("zone_info.yaml", encoding="utf8", mode="r") as f:
        zone_info = yaml.load(f, Loader=yaml.Loader)
        map_list = []
        base_path = "ui/map/"
        for map in zone_info.values():
            region = map["filename"][:4]
            zone = map["filename"][4:]
            map_list.append(base_path + region + "/" + zone + "/" + map["filename"] + "_m.tex")

        with open("map_list_from_zone_info.txt", encoding="utf8", mode="w") as f:
            for x in map_list:
                f.write(x + "\n")
        return map_list

# 实际太多了，根本用不了，建议用export_map.txt整理好的
def get_map_list():
    map_list = []
    with open("main_export_all_data.txt", encoding="utf8", mode="r") as f:
        for line in f:
            # 如果包涵ui/map/，则是地图
            if "ui/map/" in line:
                map_list.append(line.strip())
    # 写入map_list到txt文件
    with open("map_list_export.txt", encoding="utf8", mode="w") as f:
        for x in map_list:
            f.write(x + "\n")
    return map_list


def delete_png_under_folder(root):
    dirs = os.listdir(root)
    for dir in dirs:
        current = os.path.join(root, dir)
        if os.path.isdir(current):
            delete_png_under_folder(current)
        else:
            if current.endswith(".png"):
                os.remove(current)



if __name__ == '__main__':
    old_path = "F:\\ffxiv\\Resource_TT\\Saved\\UI\\地图"
    current_path = "F:\GitHub\\ffxiv-huntmaps-maker\\Saved\\UI\\地图"
    output = "F:\\GitHub\\ffxiv-huntmaps-maker\\ui\\map"
    # print(get_place_name())

    # with open("temp.txt", mode="w", encoding="utf8") as f:
    #     for value in get_action_list().items():
    #         f.write("{\"%s\",\"%s\"}," % (value[0], value[1]))
    # for value in get_action_list().items():
    #     print("{\"%s\",\"%s\"}," % (value[0], value[1]))
    tran_marks()
    # tran_zone_info()
    # rename_map(current_path, False)
    # get_map_list()
    # delete_png_under_folder(output)
    # get_map_list_from_zone_info()
