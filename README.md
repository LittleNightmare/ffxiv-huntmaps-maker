# ffxiv-huntmaps-maker

Library + CLI to annotate FFXIV in-game map assets with Elite Marks spawn positions.

**In this branch**, the path of the map is changed format likes `ui/map/n4f1/00/n4f100_m.tex`, you can see this [file](https://github.com/LittleNightmare/ffxiv-huntmaps-maker/blob/raw-map/data/export_map.txt)

## Installation

- You need python >= 3.7
- Clone repo
- switch to any virtual/conda environment you'd like to use (or not)
- cd to directory
- `pip install -r requirements.txt`
- `python annotate.py` to get a list of commands

## How to use

The process is the following:

1. In this branch, use [Alpha](https://github.com/NotNite/Alpha) to export the map files as .tex. You could find map list [here]((https://github.com/LittleNightmare/ffxiv-huntmaps-maker/blob/raw-map/data/export_map.txt))
2. Then, use [ffxiv-tex-converter](https://github.com/emarron/ffxiv-tex-converter), to covert the .tex files to .dds
2. Edit `data/config.yaml` to adjust to your preferences, especially the paths. In this branch, the `textools_path` should contain `ui` folder.
3. Assuming you just exported the original dds map files, run: `python annotate.py check_files` and, assuming this came out without any error, run `python annotate.py backup_files`. From there, you're ready to work.
4. review `zone_info.yaml` in case the asset path in the game files has changed (occasionally, SE will move a map from zonename to "zonename 00"). Remove/Add/Amend a zonename entry for the zones concerned if needed. If the zonename entry doesn't exist, the script will use the true zone name.
5. Edit the marker/legend styles in `data/config.yaml` as desired
6. Run `python annotate.py annotate_map zone_name` to annotate that zone. It will open a view of the annotated map
7. Once ready, run `python annotate.py annotate_all`. All maps will be rendered and saved (both in the project path and in original asset path)
8. With TexTools:

    * import one by one the new dds files
    * (optionally, for distribution), create a mod pack with these assets.

It can also be used as a library, from a jupyter notebook (for exampe) created in the same directory:

```python
from annotate import MapAnnotator

annotator = MapAnnotator()
```

From there, you can call the same methods. `MapAnnotator.annotate_map` will instead preview the output directly in the notebook rather than opening `Paint`.

## Reference

Information on commands, their function and use is available through the tool.

```cmd
python annotate.py [command] --help
```

## To Dos

* [ ] handle errors
* [ ] write tests

## Disclaimer

Use of the mods created with this tool is at your own risk. Square Enix does not permit the use of any third party tools, even those which do not modify the game. They have stated in interviews that they did not view parsers as a significant problem unless players use them to harass other players.

## Copyright

Copyright @ Arkhelyi, 2020.
