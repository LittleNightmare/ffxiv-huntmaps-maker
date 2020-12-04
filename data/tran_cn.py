import csv
import json
import os

import yaml


# 所有csv可以分别在ffxiv-dataming找到，国际服增加后缀_en，国服不变

# 将marks.json 翻译成中文
def tran_marks():
    BNpcName_en = []
    BNpcName_cn = []
    with open("BNpcName_en.csv", encoding="utf8", mode="r") as f:
        csv_en = csv.reader(f)
        for x in csv_en:
            BNpcName_en.append(x[1])

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
                k["name"] = table[k["name"]]
            except KeyError as e:
                try:
                    # print(k["name"] + ": " + table[k["name"].lower()])
                    k["name"] = table[k["name"].lower()]
                except KeyError as e:
                    print(e)
        with open("marks_cn.json", encoding="utf8", mode="w") as f:
            json.dump(marks_en, f, ensure_ascii=False, indent=4, sort_keys=True)


# 生成一个地名对照字典
def get_place_name(table_type_cnkey=False):
    PlaceName_en = []
    PlaceName_cn = []
    with open("PlaceName_en.csv", encoding="utf8", mode="r") as f:
        csv_en = csv.reader(f)
        for x in csv_en:
            PlaceName_en.append(x[1])

    with open("PlaceName.csv", encoding="utf8", mode="r") as f:
        csv_cn = csv.reader(f)
        for x in csv_cn:
            PlaceName_cn.append(x[1])

    table = {}
    for i in range(len(PlaceName_en)):
        if table_type_cnkey:
            table[PlaceName_cn[i]] = PlaceName_en[i]
        else:
            table[PlaceName_en[i]] = PlaceName_cn[i]

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


# 将textools一个个手动导出（有好心人提供个自动吗）的地图，从英文转换到中文
def rename_map(root):
    table = get_place_name()
    dirs = os.listdir(root)
    for dir in dirs:
        current = os.path.join(root, dir)
        if os.path.isdir(current):
            rename_map(current)
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


if __name__ == '__main__':
    root = "C:\\Users\\...\\Documents\\TexTools\\Saved\\UI\\地图"
    # tran_marks()
    # tran_zone_info()
    rename_map(root)
