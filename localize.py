#!/usr/bin/env python3

import os
import re
from typing import Callable, Dict, Optional, Tuple

import bs4
from bs4 import BeautifulSoup
import requests


class Localizer:
    def __init__(
            self,
            issue_urls: Dict[str, int],
            root_dir: str = "",
            issue_dir: str = "Issue",
            common_assets_dir: str = "common",
            overwrite_assets: bool = False) -> None:

        self.issue_urls = issue_urls
        self.base_url = None
        self.overwrite_assets = overwrite_assets

        self.root_dir = root_dir
        self.issue_dir = os.path.join(root_dir, issue_dir)

        self.common_assets_dir = common_assets_dir
        self.styles_dir = os.path.join(self.common_assets_dir, "styles")
        self.fonts_dir = os.path.join(self.common_assets_dir, "fonts")
        self.scripts_dir = os.path.join(self.common_assets_dir, "scripts")
        self.images_dir = "img"

        common_to_root = os.path.join(root_dir, common_assets_dir)

        # when making sure the directories exist, now we need to
        # frame it relative to the current working directory
        for dr in (root_dir, self.issue_dir, common_to_root, os.path.join(common_to_root, "styles"), os.path.join(common_to_root, "fonts"), os.path.join(common_to_root, "scripts"), os.path.join(self.issue_dir, "img")):
            os.makedirs(dr, exist_ok=True)

    def localize_page(self, raw_data: str, filename: str, page: int) -> str:
        """Parses a full page and localizes all resources."""
        soup = BeautifulSoup(raw_data, 'html.parser')

        # remove base href
        base_href = soup.head.find("base")
        if base_href is not None:
            self.base_url = base_href["href"]
            remove_elem(base_href)

        # download all stylesheets and refer to local copy
        css = soup.head.find_all("link", rel="stylesheet")
        for ss in css:
            ss["href"] = self.localize_item(
                ss["href"],
                rel_dir=os.path.join("..", self.styles_dir),
                abs_dir=os.path.join(self.root_dir, self.styles_dir),
                formatter=self.localize_css)

        styles = soup.find_all("style")
        for style in styles:
            style.string = self.localize_css(style.string, self.base_url, in_subdir=False)

        # delete the manifest and some other metadata
        remove_elem(soup.head.find("link", rel="manifest"))
        remove_elem(soup.head.find("meta", attrs={"name": "apple-itunes-app"}))

        og_url = soup.head.find("meta", property="og:url")
        if og_url is not None:
            og_url["content"] = os.path.join(self.issue_dir, filename)

        og_image = soup.head.find("meta", property="og:image")
        if og_image is not None:
            og_image["content"] = self.localize_item(
                og_image["content"],
                rel_dir=self.images_dir,
                abs_dir=os.path.join(self.issue_dir, self.images_dir),
                binary=True)

        # remove "web-smart" banner
        bootstrap = soup.head.find("script", class_="KGPugpigReader-bootstrap")
        if bootstrap is not None:
            prev_script = bootstrap.previous_sibling
            remove_elem(prev_script)
            remove_elem(bootstrap)

        # download all scripts and refer to local copy
        js = soup.find_all("script", src=True)
        for j in js:
            if "google" in j["src"]:
                remove_elem(j)
            else:
                j["src"] = self.localize_item(
                    j["src"],
                    rel_dir=os.path.join("..", self.scripts_dir),
                    abs_dir=os.path.join(self.root_dir, self.scripts_dir))

        # download all images
        img = soup.find_all("img")
        for i in img:
            # skip SVG elements
            if not i["src"].startswith("data:"):
                # remove preload class, which makes all images height
                # and width of 0
                if "preload" in i["class"]:
                    i["class"].remove("preload")

                i["src"] = self.localize_item(
                    i["src"],
                    rel_dir=self.images_dir,
                    abs_dir=os.path.join(self.issue_dir, self.images_dir),
                    binary=True)

        # add forward and back arrows
        if page == 1:
            nav_arrows = create_nav_arrows(page=page, prev=False)
        elif page == len(self.issue_urls):
            nav_arrows = create_nav_arrows(page=page, next=False)
        else:
            nav_arrows = create_nav_arrows(page=page)
        soup.body.insert(0, nav_arrows)

        # localize any links that refer to other pages in the issue
        links = soup.find_all("a")
        for a in links:
            if "href" in a and a["href"] in self.issue_urls:
                a["href"] = f"page{self.issue_urls[a['href']]+1}.html"

        return soup.prettify()

    def localize_item(
            self,
            url: str,
            rel_dir: str = ".",
            abs_dir: str = ".",
            binary: bool = False,
            formatter: Optional[Callable[[str, str, Dict[str, str]], str]] = None) -> str:
        """Takes a URL, downloads the resource locally, and returns
        the local path where it can be found."""
        url_parts = url.split("/")
        rel_path = os.path.join(rel_dir, url_parts[-1])
        abs_path = os.path.join(abs_dir, url_parts[-1])

        # only re-download if we don't already have the resource
        if self.overwrite_assets or not os.path.exists(abs_path):
            r = requests.get(url)
            if r.status_code == 200:
                if binary:
                    localized_content = r.content
                    if formatter is not None:
                        localized_content = formatter(localized_content, url)
                    with open(abs_path, "wb") as f:
                        f.write(localized_content)
                else:
                    localized_text = r.text
                    if formatter is not None:
                        localized_text = formatter(localized_text, url)
                    with open(abs_path, "wt") as f:
                        f.write(localized_text)
                return rel_path
            else:
                print(f"Error downloading file {url}")
                return url
        return rel_path

    def localize_one_css_url(self, match_obj: re.Match, orig_url: str, in_subdir: bool = True) -> str:
        """Given a match object matching a 'url()' CSS expression,
        this pulls the appropriate resource and returns a localized
        path."""
        url = match_obj.group(1)
        if url.startswith("'data:"):
            # this is an SVG element
            return match_obj.group(0)
        if url.startswith("."):
            url = url_rel_to_abs(url, orig_url)
        if url.lower().endswith((".ttf", ".otf", ".woff", ".woff2", ".eot")):
            rel_dir = os.path.join("..", self.fonts_dir)
            abs_dir = os.path.join(self.root_dir, self.fonts_dir)
        else:
            rel_dir = self.images_dir
            abs_dir = os.path.join(self.issue_dir, self.images_dir)
        rel_path = self.localize_item(
            url,
            rel_dir=rel_dir,
            abs_dir=abs_dir,
            binary=True)

        if in_subdir:
            return f'url("{os.path.join("..", rel_path)}")'
        else:
            return f'url("{rel_path}")'

    def localize_css(self, raw_data: str, orig_url: str, in_subdir: bool = True) -> str:
        """Searches text for 'url()' and replaces with an absolute
        URL, based on the URL of the original resource."""
        return re.sub(r"url\(['\"]?([^'\")]+)['\"]?\)", lambda m: self.localize_one_css_url(m, orig_url, in_subdir), raw_data)


def remove_elem(elem: Optional[bs4.element.Tag]):
    """Removes an element from the BeautifulSoup structure, if it exists."""
    if elem is not None:
        elem.decompose()


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


def create_nav_arrows(page: int, prev: bool = True, next: bool = True) -> bs4.element.Tag:
    html = """
<style>
.assets_icons, .assets_icons figure {
  width: 0;
  height: 0;
}

.viewer_arrows a {
  background: rgba(3,3,3,.6);
  display: block;
  line-height: 100px;
  margin-top: -60px;
  position: fixed;
  bottom: 0;
  top: 50%;
  width: 50px;
  height: 100px;
  z-index: 1000;
}

.viewer_arrows .arrow_prev {
  border-top-right-radius: 3px;
  border-bottom-right-radius: 3px;
}

.viewer_arrows .arrow_next {
  border-top-left-radius: 3px;
  border-bottom-left-radius: 3px;
  right: 0;
}

.viewer_arrows button {
  background-color: transparent;
  border: 0;
  cursor: pointer;
  fill: black;
  margin: 0;
  overflow: visible;
  padding: 0;
  text-align: center;
  width: 50px;
  height: 100%;
}

.viewer_arrows svg {
  fill: #eee;
  overflow: hidden;
  pointer-events: none;
  width: 40px;
  height: 100%;
}
</style>
<div class="assets_icons">
  <figure>
    <svg xmlns="http://www.w3.org/2000/svg">
      <symbol id="icon-back" viewBox="-322 443 75 75">
        <title>back</title>
        <path id="back-XMLID_15_" d="M-302.3,480.6c0,0,28.9,28.8,29.1,28.9c0.2,0.2,2,1.3,3.4-0.1c1.4-1.4,0.4-2.8,0.2-3
	c-0.1-0.1-25.6-25.8-25.6-25.8l25.4-25.4c0,0,1.7-1.8,0-3.5c-1.6-1.6-3.4-0.1-3.4-0.1L-302.3,480.6z"></path>	
      </symbol>
      <symbol id="icon-forward" viewBox="-322 443 75 75">
        <title>forward</title>
        <path id="forward-XMLID_15_" d="M-261.2,480.4c0,0-28.9-28.8-29.1-28.9c-0.2-0.2-2-1.3-3.4,0.1c-1.4,1.4-0.4,2.8-0.2,3
	c0.1,0.1,25.6,25.8,25.6,25.8l-25.4,25.5c0,0-1.7,1.8,0,3.5c1.6,1.6,3.4,0.1,3.4,0.1L-261.2,480.4z"></path>	
      </symbol>
    </svg>
  </figure>
</div>
<nav class="viewer_arrows">
"""
    if prev:
        html += f"""
  <a class="arrow_prev" href="page{page-1}.html">
    <button aria-hidden="true" tabindex="-1" data-tooltip="Previous">
      <svg><use xlink:href="#icon-back"></use></svg>
    </button>
  </a>
"""
    if next:
        html += f"""
  <a class="arrow_next" href="page{page+1}.html">
    <button aria-hidden="true" tabindex="-1" data-tooltip="Next">
      <svg><use xlink:href="#icon-forward"></use></svg>
    </button>
  </a>
"""
    html += """
</nav>
"""
    elems = BeautifulSoup(html, 'html.parser')
    return elems


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Localize an HTML file for the Dragon+ magazine.")
    parser.add_argument("filepath", nargs="+",
                        help="Path to one or more files to localize")
    args = parser.parse_args()

    for filepath in args.filepath:
        with open(filepath, "r") as f:
            raw_html = f.read()

        localizer = Localizer()
        converted = localizer.localize_page(raw_html, filename=filepath)

        file_parts = filepath.split(".")
        file_parts[-2] += "_localized"
        new_file = ".".join(file_parts)

        with open(new_file, "w") as f:
            f.write(converted)