#!/usr/bin/env python3

import os
import re
from typing import Callable, Optional

import bs4
from bs4 import BeautifulSoup
import requests

STYLES_DIR = "styles"
FONTS_DIR = "fonts"
SCRIPTS_DIR = "scripts"
IMG_DIR = "img"


def url_rel_to_abs(relative_url: str, from_url: str) -> str:
    """Converts a relative URL to an absolute URL, given the
    (absolute) URL of the resource where it came from."""
    abs_url_parts = from_url.split("/")[:-1]
    rel_url_parts = relative_url.split("/")
    while rel_url_parts[0].startswith("."):
        if rel_url_parts[0] == "..":
            abs_url_parts = abs_url_parts[:-1]  # chop off last dir
        rel_url_parts = rel_url_parts[1:]
    return "/".join(abs_url_parts + rel_url_parts)



def localize(url: str, local_dir: str = ".", binary: bool = False, formatter: Optional[Callable[[str, str], str]] = None) -> str:
    """Takes a URL, downloads the resource locally, and returns the
    local path where it can be found."""
    url_parts = url.split("/")
    local_path = os.path.join(local_dir, url_parts[-1])
    os.makedirs(local_dir, exist_ok=True)

    # only re-download if we don't already have the resource
    if not os.path.exists(local_path):
        r = requests.get(url)
        if r.status_code == 200:
            if binary:
                localized_content = r.content
                if formatter is not None:
                    localized_content = formatter(localized_content, url)
                with open(local_path, "wb") as f:
                    f.write(localized_content)
            else:
                localized_text = r.text
                if formatter is not None:
                    localized_text = formatter(localized_text, url)
                with open(local_path, "wt") as f:
                    f.write(localized_text)
            return local_path
        else:
            print(f"Error downloading file {url}")
            return url
    return local_path


def localize_one_css_url(match_obj: re.Match, orig_url: str, in_subdir: bool = True) -> str:
    """Given a match object matching a 'url()' CSS expression, this
    pulls the appropriate resource and returns a localized path."""
    url = match_obj.group(1)
    if url.startswith("'data:"):
        # this is an SVG element
        return match_obj.group(0)
    if url.startswith("."):
        url = url_rel_to_abs(url, orig_url)
    if url.lower().endswith((".ttf", ".otf", ".woff", ".woff2", ".eot")):
        local_dir = FONTS_DIR
    else:
        local_dir = IMG_DIR
    local_path = localize(url, local_dir, binary=True)

    if in_subdir:
        return f'url("{os.path.join("..", local_path)}")'
    else:
        return f'url("{local_path}")'


def localize_css(raw_data: str, orig_url: str, in_subdir: bool = True) -> str:
    """Searches text for 'url()' and replaces with an absolute URL,
    based on the URL of the original resource."""
    return re.sub(r"url\(['\"]?([^'\")]+)['\"]?\)", lambda m: localize_one_css_url(m, orig_url, in_subdir), raw_data)


def remove_elem(elem: Optional[bs4.element.Tag]):
    """Removes an element from the BeautifulSoup structure, if it exists."""
    if elem is not None:
        elem.decompose()


def localize_page(raw_data: str) -> str:
    base_url = None
    soup = BeautifulSoup(raw_html, 'html.parser')

    # change base href -- not really critical, but why not
    base_href = soup.head.find("base")
    if base_href is not None:
        base_url = base_href["href"]
        base_href["href"] = FILENAME

    # download all stylesheets and refer to local copy
    css = soup.head.find_all("link", rel="stylesheet")
    for ss in css:
        ss["href"] = localize(ss["href"], STYLES_DIR, formatter=localize_css)

    styles = soup.find_all("style")
    for style in styles:
        style.string = localize_css(style.string, base_url, in_subdir=False)

    # delete the manifest and some other metadata
    remove_elem(soup.head.find("link", rel="manifest"))
    remove_elem(soup.head.find("meta", attrs={"name": "apple-itunes-app"}))

    og_url = soup.head.find("meta", property="og:url")
    if og_url is not None:
        og_url["content"] = FILENAME

    og_image = soup.head.find("meta", property="og:image")
    if og_image is not None:
        og_image["content"] = localize(og_image["content"], IMG_DIR, binary=True)

    # remove "web-smart" banner
    bootstrap = soup.head.find("script", class_="KGPugpigReader-bootstrap")
    if bootstrap is not None:
        prev_script = bootstrap.previous_sibling
        remove_elem(prev_script)
        remove_elem(bootstrap)

    # download all scripts and refer to local copy
    js = soup.find_all("script", src=True)
    for j in js:
        j["src"] = localize(j["src"], SCRIPTS_DIR)

    # download all images
    img = soup.find_all("img")
    for i in img:
        i["src"] = localize(i["src"], IMG_DIR, binary=True)

    return soup.prettify()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Localize an HTML file for the Dragon+ magazine.")
    parser.add_argument("filepath", nargs="+",
                        help="Path to one or more files to localize")
    args = parser.parse_args()

    for filepath in args.filepath:
        with open(filepath, "r") as f:
            raw_html = f.read()

        converted = localize_page(raw_html)

        file_parts = filepath.split(".")
        file_parts[-2] += "_localized"
        new_file = ".".join(file_parts)

        with open(new_file, "w") as f:
            f.write(converted)