"""Library + CLI to annotate FFXIV in-game map assets with Elite Marks spawn positions.

Copyright @ Arkhelyi, 2019"""

from collections import defaultdict
import inspect
from operator import itemgetter
import os
import pathlib
import shutil
import subprocess
import yaml

import fire
import numpy as np
import pyperclip
from PIL import Image, ImageDraw

from helpers import ZoneApi, MarksHelper, Position, drop_shadow, m2c, Legend


class MapAnnotator:
    """Library + CLI to annotate FFXIV in-game map assets with Elite Marks spawn positions.

    To perform this, it relies on 3 configuration files:
    - data/zone_info.yaml: file generated from xivapi mapping a zone name to its region, map filename, scale factor
    - data/marks.json: static data file mapping a mark to its rank, zone and spawn positions
    - data/config.yaml: configuration for paths, marker style, legend style and position

    In addition to the python requirements, it requires ImageMagick to be installed (path can be in
    user $PATH or provided in configuration)"""

    def __init__(self):
        with open("data/config.yaml", "rt", encoding="utf-8") as fp:
            a = yaml.load_all(fp, Loader=yaml.Loader)
            self._config = {k: v for i in a for k, v in i.items()}

        self._base_path = pathlib.Path(
            self._config["tool"]["textools_path"]
        ).expanduser()
        self._project_path = pathlib.Path(
            self._config["tool"]["project_path"]
        ).expanduser()
        self._magickpath = self._config["tool"]["imagemagick_path"] or shutil.which(
            "magick"
        )

        zones = self._config["zones"]
        ZoneApi(zones.keys()).load_zone_info(zones)
        self._zones = zones
        self._Mark, self._marks = MarksHelper.load_marks("data/marks_cn.json")
        self._iscli = inspect.stack()[-2].function == "Fire"

    def _get_path(self, name, project=False, backup=False, ext=None):
        base = self._base_path if not project else self._project_path
        base = base / "Saved" / "UI" / "地图"
        region = self._zones[name]["region"]
        zone = self._zones[name].get("zonename", name)
        file = self._zones[name]["filename"]
        bck = "_backup" if backup else ""
        ext = ext or "dds"
        return (base / region / zone / (file + "_m" + bck)).with_suffix("." + ext)

    def _get_zone_marks(self, zone, rank_remap=False):
        marks = {
            mark.name: (mark.rank, mark.spawns)
            for mark in self._marks
            if mark.zone == zone
        }

        def remap_rank(lmarks, rank):
            """Given a dictionary {mark_name: mark_rank}, will rewrite the values for the given
            rank to account for multiple occurences of it.
            Example: A -> A1, A2"""
            fmarks = [k for k, v in lmarks.items() if v[0] == rank]
            for i, m in enumerate(sorted(fmarks)):
                lmarks[m] = (f"{rank}{i+1}", lmarks[m][1])

        if rank_remap:
            remap_rank(marks, "A")
            remap_rank(marks, "B")
        return marks

    def check_files(self, backup=False):
        """Verify the presence of asset backup files (used as source for map annotation)."""

        for name in self._zones:
            path = self._get_path(name, backup=backup)
            if not path.exists():
                print(f"MISSING: file '{name}' @ '{path}'")
        print("File check complete.")

    def check_spawn_points(self, threshold=0.5):
        """List all spawn points that are closer to each other than `threshold` (default 0.5y)"""

        def distance(s1, s2):
            from math import sqrt

            return sqrt((s2[0] - s1[0]) ** 2 + (s2[1] - s1[1]) ** 2)

        suspicious = defaultdict(list)

        for zone in self._zones:
            spawnset = defaultdict(list)
            marks = self._get_zone_marks(zone)
            for mark, (_, spawns) in marks.items():
                for spawn in spawns:
                    spawnset[tuple(spawn)].append(mark)

            spawn_list = list(spawnset.keys())
            for i1, spawn1 in enumerate(spawn_list):
                for spawn2 in spawn_list[i1 + 1 :]:
                    if distance(spawn1, spawn2) <= threshold:
                        suspicious[zone].append([spawn1, spawn2])

        return suspicious

    def backup_files(self, warning=True):
        """Backup asset export files.

        Backup files are used as source to draw annotations so they *need* to be the original files.
        The annotation process replaces the original export, so calling this function after some maps
        have been annotated will result in already annotated source files and the original assets will
        need to be re-exported with TexTools and backed-up again.

        Call this method with warning=False to execute."""
        if warning:
            print(
                "Be careful! This command should only be used after a fresh export of original in-game assets."
            )
            print(
                "Otherwise, you will overwrite your backups and need to re-export original assets before annotating maps."
            )
            print("Call this method with warning=False to execute.")
            return
        self.check_files()
        for name in self._zones:
            path = self._get_path(name)
            bpath = self._get_path(name, backup=True)
            shutil.copy(path, bpath)
        print("Backup complete.")

    def annotate_map(self, name, save=False, show=True):
        """Annotate the map of the zone `name`. Optionally save the modified asset file and its png preview

        Saves are made both in the TexTools folder for easy import and to the map project folder for repo update.
        """
        map_layer = Image.open(self._get_path(name, backup=True))

        marker_layer = Image.new("RGBA", map_layer.size, color=(0, 0, 0, 0))

        scale = self._zones[name]["scale"]
        zone_marks = self._get_zone_marks(name, True)
        spawns = defaultdict(dict)
        for mark, (rank, spots) in zone_marks.items():
            for p in spots:
                spawns[tuple(p)][mark] = rank
        for spawn, marks in spawns.items():
            screen_position = Position(m2c(spawn[0], scale), m2c(spawn[1], scale))
            self._draw_marker(marker_layer, screen_position, marks)

        marker_layer = drop_shadow(
            marker_layer,
            offset=Position(*self._config["marker"]["shadow_offset"]),
            shadow_color=self._config["marker"]["shadow_color"],
            iterations=self._config["marker"]["shadow_iterations"],
            scale=self._config["marker"]["shadow_scale"],
            direction=self._config["marker"]["shadow_direction"],
        )

        marks = {name: rank for name, (rank, _) in zone_marks.items()}
        new_map = Image.alpha_composite(map_layer, marker_layer)
        legend_rows = self._zones[name]["legend"]["rows"]
        legend_position = Position(*self._zones[name]["legend"]["position"])
        complete_map = self._draw_legend(new_map, marks, legend_rows, legend_position)

        if save:
            self._save_map(complete_map, name)
        if self._iscli and show:
            complete_map.show(title=name)
            return
        return complete_map

    def _draw_legend(self, img, marks, rows, position):
        legend = Legend(self._config).draw(img.size, position, marks, rows)
        return Image.alpha_composite(img, legend)

    def _draw_marker(self, img, position, marks):
        draw = ImageDraw.Draw(img)

        size = self._config["marker"]["size"]
        inner_size = size * self._config["marker"]["inner_size_scale"]
        colors = self._config["colors"]
        box = (*(position - 0.5 * size), *(position + 0.5 * size))
        inner_box = (*(position - 0.5 * inner_size), *(position + 0.5 * inner_size))

        angle = 180
        for angle, rank in zip(range(180, 180 + 360, 90), ["B1", "B2", "A1", "A2"]):
            if rank in marks.values():
                draw.pieslice(
                    box, angle, angle + 90, fill=colors[rank], outline=None, width=0
                )
            angle += 90

        if "S" in marks.values():
            draw.ellipse(inner_box, fill=colors["S"], outline=None, width=0)

        if "SS" in marks.values() or "SSs" in marks.values():
            rank = next(
                iter(marks.values())
            )  # There should be only one rank if it's SS or SSs
            draw.ellipse(box, fill=colors[rank], outline=None, width=0)

        return img

    def _save_map(self, img, name):
        src = self._get_path(name, ext="bmp")
        dst = src.with_suffix(".dds")
        img.save(src, format="bmp")
        cmd = f'{self._magickpath} convert -define dds:compression=dxt1 -define dds:mipmaps=0 "{src}" "{dst}"'
        subprocess.run(cmd, capture_output=True)
        src.unlink()
        pdst = self._get_path(name, ext="dds", project=True)
        os.makedirs(os.path.dirname(pdst), exist_ok=True)
        shutil.copy(dst, pdst)

        preview_dst = pdst.with_suffix(".png")
        img.save(preview_dst, format="png")

    def annotate_all(self):
        """Annotate and save all maps.

        Saves are made both in the TexTools folder for easy import and to the map project folder for repo update.
        """
        for zone in self._zones:
            self.annotate_map(zone, save=True, show=False)

    def generate_thumbnail_table(self):
        """Generate html code for the collapsable preview tables used in the map repo's README.

        Results is copied into the OS' clipboard"""
        document = ""
        for expansion, expac_name in self._config["expansions"].items():
            expac_data = defaultdict(list)
            for zone, info in self._zones.items():
                if info["expansion"] == expansion:
                    if info["region"] == "Norvrandt":
                        if len(expac_data["Norvrandt 1"]) < 3:
                            expac_data["Norvrandt 1"].append(
                                (info.get("zonename", zone), info["filename"])
                            )
                        else:
                            expac_data["Norvrandt 2"].append(
                                (info.get("zonename", zone), info["filename"])
                            )
                    else:
                        expac_data[info["region"]].append(
                            (info.get("zonename", zone), info["filename"])
                        )

            for zones in expac_data.values():
                zones.sort(key=itemgetter(0))

            n_rows = max([len(v) for v in expac_data.values()])

            url_template = self._config["tool"]["preview_url_template"]
            item_template = '<a href="{url}"><img src="{url}" width="{w}"/>'
            header_template = ":---: | "
            title = "| "
            header = "| "

            summary = f"<details><summary><b>{expac_name}</b></summary>\n\n"
            title = summary + title
            for region in sorted(expac_data.keys()):
                title += f"{region} | "
                header += header_template
                table = title + "\n" + header + "\n"

            for i in range(n_rows):
                line = "| "
                for region in sorted(expac_data.keys()):
                    try:
                        zone, file = expac_data[region][i]
                        if "Norvrandt" in region:
                            region = region[:-2]
                        url = url_template.format(region=region, zone=zone, file=file)
                        item = item_template.format(url=url, w=150)
                        line += f"{item} |"
                    except IndexError:
                        line += "   | "
                table += line + "\n"
            table += "\n</details>\n\n"
            document += table
        pyperclip.copy(document)

    def blend_map(self, name, from_backup=True, save=False, show=True):
        """Blend the base asset image (live, likely annotated or backup) with the relevant background.

        Saves are in the map project folder for repo update."""

        maskpath_map = {
            "ARR": "arrhw",
            "HW": "arrhw",
            "SB": "sb",
            "SHB": "shb",
            "EW": "shb",  # the parchment texture seems to be the same since shb (at least) and my shb cleanup is better than the ew's one
            "DT": "shb",
        }
        maskbase_path = self._project_path / "Blended" / "masks"
        mask_name = maskpath_map[self._zones[name]["expansion"]] + "_mask.png"
        mask_path = maskbase_path / mask_name

        map_layer = Image.open(self._get_path(name, backup=from_backup))
        mask_layer = Image.open(mask_path)

        if map_layer.size != mask_layer.size:
            raise ValueError

        np_map = np.array(map_layer)
        np_mask = np.array(mask_layer)
        np_blended = np.zeros(np_map.shape, dtype=np_map.dtype)
        np_blended[:, :, :3] = (
            np_map.astype(float)[:, :, :3] * np_mask[:, :, :3] / 255.0
        )
        np_blended[:, :, 3] = np_map[:, :, 3]
        blended = Image.fromarray(np_blended)

        if save:
            self._save_blended_map(blended, name)
        if self._iscli and show:
            blended.show(title=name)
            return
        return blended

    def _save_blended_map(self, img, name):
        filepath = self._project_path / "Blended" / (name + ".png")
        img.save(filepath, format="png")

    def blend_all(self, from_backup=True):
        """Blend and save all maps.

        Saves are made in the map project folder for repo update."""
        for zone in self._zones:
            self.blend_map(zone, save=True, from_backup=from_backup, show=False)


if __name__ == "__main__":
    fire.Fire(MapAnnotator)
