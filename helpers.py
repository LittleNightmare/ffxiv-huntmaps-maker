from collections import namedtuple
from copy import deepcopy
import json
import yaml
from math import pi, cos, sin
from operator import itemgetter
import re

from PIL import Image, ImageFilter, ImageFont, ImageDraw, ImageColor
import requests


def yml_tuple_constructor(loader, node):
    """This is to convert the string written as a tuple into a python tuple
    
    from https://stackoverflow.com/a/48452275t"""

    def parse_tup_el(el):
        """try to convert into int or float else keep the string"""
        if el.isdigit():
            return int(el)
        try:
            return float(el)
        except ValueError:
            return el

    value = loader.construct_scalar(node)
    # remove the ( ) from the string, strip spaces and split into elements
    tup_elements = value[1:-1].replace(" ", "").split(",")
    # remove the last element if the tuple was written as (x,b,)
    if tup_elements[-1] == "":
        tup_elements.pop(-1)
    tup = tuple(map(parse_tup_el, tup_elements))
    return tup


# !tuple is my own tag name, I think you could choose anything you want
yaml.add_constructor("!tuple", yml_tuple_constructor)
# this is to spot the strings written as tuple in the yaml
pattern = re.compile(r"\(([+-]?([0-9]*[.])?[0-9]+, ?)+([+-]?([0-9]*[.])?[0-9]+)?\)")
yaml.add_implicit_resolver("!tuple", pattern)


class MarksHelper:
    """Helper class to load the marks.json file.

    Nothing fancy and only the load method is useful on a regular basis. Other methods
    were used to put the data in a good shape."""

    def __init__(self):
        pass

    @staticmethod
    def dump_marks(marklist, filename):
        """Dump the list of Mark namedtuples in json"""
        new_list = [t._asdict() for t in marklist]
        if filename == "str":
            return json.dumps(new_list)
        with open(filename, "wt", encoding="utf8") as fp:
            json.dump(new_list, fp)

    @staticmethod
    def load_marks(filename):
        """Load the json file and build the list of namedtuples"""
        with open(filename, "rt", encoding='utf-8') as fp:
            marks = json.load(fp)

        Mark = namedtuple("Mark", marks[0])
        return Mark, [Mark(**mark) for mark in marks]

    @staticmethod
    def sort_marks(filename):
        """Load, sort the data and dump it back.
        
        Sort the marks by zone, rank, name
        Sort the spawn points by x, y"""
        with open(filename, "rt", encoding="utf8") as fp:
            marks = json.load(fp)

        marks.sort(key=itemgetter("zone", "rank", "name"))
        for mark in marks:
            mark["spawns"] = sorted(mark["spawns"], key=itemgetter(0, 1))
        with open("new_" + filename, "wt", encoding="utf8") as fp:
            json.dump(marks, fp)


class ZoneApi:
    """Helper class to query xivapi.com and collect zone information"""

    def __init__(self, zones):
        self.base_url = "https://xivapi.com"
        self.zones = zones
        self.cachename = "data/zone_info"

    def _get_zone_url(self, name):
        """query xivapi to find the url to access zone info.

        There's a trick to Mor Dhona as the zone exists under multiple id"""
        resp = requests.get(f"{self.base_url}/search?indexes=PlaceName&string={name}")
        if resp.ok:
            results = resp.json()["Results"]
            candidates = []
            for res in results:
                if res["Name"] == name:
                    candidates.append(res)
            if len(candidates) > 1:
                if name == "Mor Dhona":
                    return next((item for item in candidates if item["ID"] == 26))[
                        "Url"
                    ]
                raise Exception(candidates)
            return candidates[0]["Url"]
        else:
            raise Exception(resp)

    def get_zone_info(self, name):
        """Get the info about a zone"""
        zone_url = self._get_zone_url(name)
        resp = requests.get(f"{self.base_url}{zone_url}")
        if resp.ok:
            results = resp.json()["Maps"][0]
            return results
        else:
            raise Exception(resp)

    def get_zone_data(self, info):
        """Build the data structure for the zone"""
        region = info["PlaceNameRegion"]["Name"]
        size_factor = info["SizeFactor"]
        filename = info["MapFilenameId"].replace("/", "")
        return {"region": region, "scale": size_factor, "filename": filename}

    def get_all_zone_info(self):
        """Collect all information"""
        results = {}
        for zone in self.zones:
            info = self.get_zone_info(zone)
            results[zone] = self.get_zone_data(info)
        return results

    def save_zone_info(self, zones, as_json=False):
        """Save the data, either as yaml (default) or json"""
        if as_json:
            with open(self.cachename + ".json", "wt", encoding="utf-8") as fp:
                json.dump(zones, fp)
                return
        with open(self.cachename + ".yaml", "wt", encoding="utf8") as fp:
            yaml.safe_dump(zones, fp)

    def load_zone_info(self, zones=None):
        """Load the data (yaml only)"""
        with open(self.cachename + ".yaml", "rt", encoding="utf-8") as fp:
            info = yaml.load(fp, Loader=yaml.Loader)
        if zones:
            for zone in list(zones.keys()):
                zones[zone].update(info[zone])
            return
        return info


class Position:
    """Position class that represents a 2-tuple of coordinates and provide helpful
    functions to operate on those.

    Accessing 'other''s values is done through indexers in order to be compatible
    with coordinates passed as lists or tuples."""

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __add__(self, other):
        try:
            return Position(self.x + other[0], self.y + other[1])
        except TypeError:
            try:
                return Position(self.x + other, self.y + other)
            except TypeError:
                raise "Position expect to be added to a Position-like or a scalar"

    def __radd__(self, other):
        return self + other

    def __mul__(self, other):
        try:
            return Position(self.x * other[0], self.y * other[1])
        except TypeError:
            try:
                return Position(self.x * other, self.y * other)
            except TypeError:
                raise "Position expect to be multiplied by a Position-like or a scalar"

    def __rmul__(self, other):
        return self * other

    def __neg__(self):
        return Position(-self.x, -self.y)

    def __sub__(self, other):
        try:
            return Position(self.x - other[0], self.y - other[1])
        except TypeError:
            try:
                return Position(self.x - other, self.y - other)
            except TypeError:
                raise "Position expect to be substracted from a Position-like or a scalar"

    def __rsub__(self, other):
        return self.__neg__() + other

    def __getitem__(self, index):
        if index == 0:
            return self.x
        if index == 1:
            return self.y

    def __setitem__(self, index, value):
        if index == 0:
            self.x = value
        if index == 1:
            self.y = value

    def __iter__(self):
        return (self.__dict__[item] for item in sorted(self.__dict__))

    def __repr__(self):
        return f"{self.__class__.__name__}({self.x},{self.y})"


def compute_columns(n_items, n_rows):
    """Compute the required number of columns given a number of items
    n_items to be displayed in a grid n_rows x n_cols"""
    if n_rows > n_items:
        return n_items, 1
    d = n_items // n_rows
    n_cols = d + (1 if n_items % n_rows else 0)
    return n_rows, n_cols


def m2c(pos, scale=100):
    """Convert map coordinates to screen/pixel coordinates"""
    return round((pos - 1) * scale * 0.01 / 40.85 * 2048)


def c2m(pos, scale=100):
    """Convert screen/pixel coordinates to map coordinates"""
    return pos * 40.85 * 100 / 2048 / scale + 1


def drop_shadow(img, offset, shadow_color, iterations=5, scale=1, direction=None):
    """Compute a drop shadow, configured by color, offset and iterations.

    scale shouldn't be used as results aren't great.
    direction='radial' will layer multiple shadows in all cardinal directions"""
    alpha = img.getchannel("A")

    base_shadow = Image.new("RGBA", img.size, color=shadow_color)
    base_shadow.putalpha(alpha)

    for i in range(iterations):
        base_shadow = base_shadow.filter(ImageFilter.BLUR)

    if direction == "radial":
        radial_steps = 4
        radial_angle_shift = 2 * pi / radial_steps
        x, y = -offset.x, -offset.y
        shadow = base_shadow.transform(
            base_shadow.size, Image.AFFINE, (scale, 0, x, 0, scale, y)
        )
        for theta in [i * radial_angle_shift for i in range(1, 4)]:
            x, y = x * cos(theta) - y * sin(theta), x * sin(theta) + y * cos(theta)
            temp_shadow = base_shadow.transform(
                base_shadow.size, Image.AFFINE, (scale, 0, x, 0, scale, y)
            )
            shadow = Image.alpha_composite(temp_shadow, shadow)
    else:
        shadow = base_shadow.transform(
            base_shadow.size, Image.AFFINE, (scale, 0, -offset.x, 0, scale, -offset.y)
        )
    return Image.alpha_composite(shadow, img)


class Legend:
    """Helper class to draw the legend on a map"""

    def __init__(self, config):
        self.inner_offset = Position(
            *config["legend"]["inner_offset"]
        )  # distance between legend border and legend items
        self.shadow_offset = Position(
            *config["legend"]["shadow_offset"]
        )  # offset to shift the shadow with
        self.column_space = config["legend"]["column_spacing"]  # Space between colum
        self.line_space = config["legend"][
            "line_spacing"
        ]  # Space between rows of items
        self.mark_scale = config["legend"][
            "mark_scale"
        ]  # Percentage by which we scale the marker to the text height
        self.font_stroke = config["legend"]["font_stroke"]  # font outline size
        self.space = config["legend"][
            "border_space"
        ]  # spacing between the two rectangles forming the border
        self.font = ImageFont.truetype(
            config["legend"]["font"], config["legend"]["font_size"]
        )
        self.shadow_color = config["legend"]["shadow_color"]
        self.shadow_iterations = config["legend"]["shadow_iterations"]
        self.colors = config["colors"]

    def draw(self, img_size, position, marks, rows):
        img = Image.new("RGBA", img_size, color=(0, 0, 0, 0))

        position = Position(*position)  # ensure Position object
        inner_position = position + self.inner_offset
        n_items = len(marks)
        rows, columns = compute_columns(n_items, rows)
        max_height = self._check_height(img, marks)

        # Initialize the size of the legend. Height is already determined but width
        # will be updated as we draw.
        size = Position(
            (columns - 1) * self.column_space,
            rows * max_height + (rows - 1) * self.line_space,
        )

        current_position = deepcopy(inner_position)
        max_width = 0
        grid_list = [
            (r, c) for c in range(1, columns + 1) for r in range(1, rows + 1)
        ]  # this is a list of grid coordinates
        for grid_pos, (mark, rank) in zip(grid_list, marks.items()):
            if mark:
                img, item_size = self._draw_legend_item(
                    img, current_position, mark, rank
                )
                max_width = max(max_width, item_size.x)

                if grid_pos[0] == rows or (
                    ((grid_pos[1] - 1) * rows + grid_pos[0]) == n_items
                ):
                    size.x += max_width

                if grid_pos[0] + 1 <= rows:
                    current_position.y += max_height + self.line_space
                else:
                    current_position.x += max_width + self.column_space
                    current_position.y = inner_position.y
                    max_width = 0

        img = drop_shadow(
            img, self.shadow_offset, self.shadow_color, self.shadow_iterations
        )
        return self._draw_border(img, position, size + 2 * self.inner_offset)

    def _check_height(self, img, marks):
        """precompute the max height of the lines necessary to draw the marks' names"""
        draw = ImageDraw.Draw(img)
        max_height = 0
        for mark in marks.keys():
            if mark:
                _, h = draw.textsize(
                    mark, font=self.font, stroke_width=self.font_stroke
                )
                max_height = max(max_height, h)

        return max_height

    def _draw_legend_item(self, img, position, mark_name, mark_rank):
        """Draw one item of the legend"""
        draw = ImageDraw.Draw(img)

        rank_label = {
            "A1": "A",
            "A2": "A",
            "B1": "B",
            "B2": "B",
            "S": "S",
            "SS": "SS",
            "SSs": "SS",
        }
        label = f"{mark_name} ({rank_label[mark_rank]})"
        _, hc = draw.textsize(
            "a", font=self.font, stroke_width=1
        )  # Determine the height of the text's baseline
        w, h = draw.textsize(label, font=self.font, stroke_width=1)  # Actual text size

        draw.ellipse(
            [
                *(position + (0, (1 - self.mark_scale) * 0.5 * hc)),
                *(position + (self.mark_scale * hc, (1 + self.mark_scale) * 0.5 * hc)),
            ],
            fill=self.colors[mark_rank],
            outline=None,
            width=0,
        )
        draw.text(
            position + (hc * self.mark_scale * 1.75, 0),
            label,
            fill="white",
            font=self.font,
            stroke_width=self.font_stroke,
            stroke_fill="black",
        )

        size = Position(hc * self.mark_scale * 1.75 + w, h)
        return img, size

    def _draw_border(self, img, position, size):
        """Draw the legend's border"""
        border = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(border)

        draw.rectangle(
            [*position, *(position + size)],
            fill=ImageColor.getrgb("#ddbf77") + (127,),
            outline="#a07d4f",
            width=3,
        )
        draw.rectangle(
            [*(position + self.space), *(position + size - self.space)],
            fill=None,
            outline="#a07d4f",
            width=1,
        )
        border = drop_shadow(
            border, self.shadow_offset, self.shadow_color, self.shadow_iterations
        )
        return Image.alpha_composite(border, img)
