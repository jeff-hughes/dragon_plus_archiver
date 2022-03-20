# Dragon+ Magazine Archiver

This is a basic script that can be used to download a single issue or multiple issues of Dragon+ magazine. The online format is nice, but it makes it difficult for archival purposes. The tool will download the HTML and all assets (images, scripts, etc.) and localize them so that the pages refer to the local versions of those assets.

To use this script, first clone the git repo:

```bash
git clone https://github.com/jeff-hughes/dragon_plus_archiver.git
cd dragon_plus_archiver
```

Then, create a Python virtual environment and install the necessary Python packages:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Then, either make the `archive.py` file executable and run it directly:

```bash
chmod +x archive.py
./archive.py --help
```

or run using Python:

```bash
python archive.py --help
```

NOTE: These instructions are for Unix-based systems; people on Windows may need to make some adjustments to the commands above.

After running the script, check the `outdir` (`./data` by default) to view the pages. Open `index.html` for an overall list of archived issues,
or view a specific issue by navigating to the directory for that issue.

## Copyright

This project is not affiliated in any way with Dragon+ Magazine or Wizards of the Coast, and they retain all copyrights to the material. This tool is to be used for personal archiving purposes only, and must not be used to redistribute material.