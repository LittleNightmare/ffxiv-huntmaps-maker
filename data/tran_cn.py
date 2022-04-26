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
                    print(k["name"]+" not exist cn name")
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
            PlaceName_en.append((x[0], x[1]))

    with open("PlaceName.csv", encoding="utf8", mode="r") as f:
        csv_cn = csv.reader(f)
        for x in csv_cn:
            PlaceName_cn.append((x[0], x[1]))

    table = {}
    for i in range(len(PlaceName_en)):
        if table_type_cnkey:
            if PlaceName_cn[i][0] == PlaceName_en[i][0]:
                table[PlaceName_cn[i][1]] = PlaceName_en[i][1]
        else:
            try:
                if PlaceName_en[i][0] == PlaceName_cn[i][0]:
                    table[PlaceName_en[i][1]] = PlaceName_cn[i][1]
            except IndexError as e:
                print(PlaceName_en[i][1])
                table[PlaceName_en[i][1]] = "Null"

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
    # 这里可以控制中文转英文或相反,True 中转英
    table = get_place_name(False)
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


# 生成一个需要导出的地图资源表
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


if __name__ == '__main__':
    # path = "C:\\Users\\lvhao\\Documents\\TexTools\\Saved\\UI\\地图"
    new_path = "F:\\ffxiv\\Resource_TT\\Saved\\UI\\地图"
    print(get_place_name())
    # tran_marks()
    # tran_zone_info()
    # rename_map(new_path)
    # get_map_list()
