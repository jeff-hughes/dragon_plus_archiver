#!/usr/bin/env python3

import os
import re
import time
from typing import Dict, List

import requests
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

DRIVER_OPTIONS = ["firefox", "chromium", "chrome", "edge", "safari", "ie", "webkit"]

ISSUE_TEMPLATE = """
<li>
  <div>
    <a href="{{ISSUE_URL}}"><img src="{{IMAGE}}" /></a>
    <h2><a href="{{ISSUE_URL}}">Issue {{ISSUE_NUM}}</a></h2>
    <p><strong>Release Date:</strong> {{RELEASE_DATE}}</p>
  </div>
</li>
"""


def start_driver(driver_type: str) -> WebDriver:
    """Initializes one of the available Selenium web drivers and returns it."""
    if driver_type not in DRIVER_OPTIONS:
        raise ValueError(f"Driver type not one of the following:\n{', '.join(DRIVER_OPTIONS)}")
    if driver_type == "firefox":
        import selenium.webdriver.firefox as drv
    elif driver_type == "chromium":
        import selenium.webdriver.chromium as drv
    elif driver_type == "chrome":
        import selenium.webdriver.chrome as drv
    elif driver_type == "edge":
        import selenium.webdriver.edge as drv
    elif driver_type == "safari":
        import selenium.webdriver.safari as drv
    elif driver_type == "ie":
        import selenium.webdriver.ie as drv
    elif driver_type == "webkit":
        import selenium.webdriver.webkitgtk as drv

    service = drv.service.Service(log_path=os.devnull)
    driver = drv.webdriver.WebDriver(service=service)
    return driver

def find_existing_issues(outdir: str) -> List[int]:
    subdirs = [o for o in os.listdir(outdir) if os.path.isdir(os.path.join(outdir, o))]
    existing_issues = []
    for d in subdirs:
        match = re.fullmatch(r".*Issue ([0-9]+)", d)
        if match:
            existing_issues.append(int(match.group(1)))
    return existing_issues


def get_issue_metadata(driver: WebDriver) -> List[Dict[str, str]]:
    """From the main page, get the list of issues."""
    driver.get("https://dnd.wizards.com/content/dragon")
    time.sleep(1)

    # click "no thanks" on the cookie banner to get it off the screen
    cookie_button = driver.find_element(By.CLASS_NAME, "decline-button")
    cookie_button.click()
    time.sleep(1.5)

    issue_metadata = []

    issue_container = driver.find_element(By.CLASS_NAME, "module_dragon-magazine")

    loop = True
    while loop:
        try:
            more_button = issue_container.find_element(By.CLASS_NAME, "more-button")
            coordinates = more_button.location_once_scrolled_into_view
            driver.execute_script(f"window.scrollTo({coordinates['x']}, {coordinates['y']});")
            visible_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(more_button))
            visible_button.click()
            time.sleep(0.5)
        except NoSuchElementException:
            loop = False

    issue_list = issue_container.find_element(By.CLASS_NAME, "articles")
    issues = issue_list.find_elements(By.TAG_NAME, "article")
    issues = list(reversed(issues))
    for i, iss in enumerate(issues):
        img_div = iss.find_element(By.CLASS_NAME, "magazine-image")
        img = img_div.find_element(By.TAG_NAME, "img")
        img_url = img.get_dom_attribute("src")

        date_p = iss.find_element(By.CLASS_NAME, "magazine-date")
        date_a = date_p.find_element(By.TAG_NAME, "a")
        date_txt = date_a.text
        date_pieces = date_txt.split(":")
        date = date_pieces[1].strip()

        issue_metadata.append({"issue": i, "img": img_url, "date": date})

    return issue_metadata


def create_index(issue_metadata: Dict[str, str], outdir: str = "") -> None:
    existing_issues = find_existing_issues(outdir)
    existing_issues.sort()

    img_dir = os.path.join(outdir, "img")
    os.makedirs(img_dir, exist_ok=True)

    issue_list = ""
    for ex in existing_issues:
        iss = issue_metadata[ex - 1]
        num_with_zeros = str(ex).zfill(2)

        # download image
        img_path = os.path.join(img_dir, f"issue{num_with_zeros}.png")
        if not os.path.exists(img_path):
            r = requests.get(iss["img"])
            if r.status_code == 200:
                with open(img_path, "wb") as f:
                    f.write(r.content)
            else:
                print(f"Error downloading image {iss['img']}")

        tmpl = ISSUE_TEMPLATE
        tmpl = tmpl.replace("{{ISSUE_NUM}}", num_with_zeros)
        tmpl = tmpl.replace("{{ISSUE_URL}}", f"./Issue {num_with_zeros}/page1.html")
        tmpl = tmpl.replace("{{IMAGE}}", f"./img/issue{num_with_zeros}.png")
        tmpl = tmpl.replace("{{RELEASE_DATE}}", iss["date"])
        issue_list += tmpl
    
    with open("index.tmpl", "r") as f:
        final_page = f.read()
    final_page = final_page.replace("{{ISSUE_LIST}}", issue_list)

    with open(os.path.join(outdir, "index.html"), "w") as f:
        f.write(final_page)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create an index of issues of Dragon+ magazine.")
    parser.add_argument("-o", "--outdir", nargs="?", default="./data",
                        help="Directory to place output files.")
    parser.add_argument("-d", "--driver", nargs="?", default="firefox",
                        help=f"Which web driver to use. Choose from: {', '.join(DRIVER_OPTIONS)}")
    args = parser.parse_args()

    driver = start_driver(args.driver)
    issue_metadata = get_issue_metadata(driver)
    create_index(issue_metadata, args.outdir)

    driver.close()