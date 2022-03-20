#!/usr/bin/env python3

import os
import re
import time
from typing import List

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from localize import Localizer
from create_index import get_issue_metadata, create_index

DRIVER_OPTIONS = ["firefox", "chromium", "chrome", "edge", "safari", "ie", "webkit"]

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


def get_issues_list(driver: WebDriver) -> List[WebElement]:
    """From the main page, get the list of issues."""
    driver.get("https://dnd.dragonmag.com")
    time.sleep(1)

    issue_list = driver.find_element(By.CLASS_NAME, "KGDocPicker_editionsList")
    issues = issue_list.find_elements(By.TAG_NAME, "li")
    issues = list(reversed(issues))
    # for i in issues:
    #     print(i.text)

    return issues


def click_issue_button(driver: WebDriver, issue_elem: WebElement) -> None:
    """Given an issue, this finds the button and clicks it."""
    issue_button = issue_elem.find_element(By.TAG_NAME, "button")
    driver.execute_script("arguments[0].scrollIntoView();", issue_button)
    visible_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(issue_button))
    visible_button.click()


def return_home(driver: WebDriver) -> None:
    """While viewing a particular issue, this finds the home button and clicks it to return to the main page with the list of issues."""
    home_button = driver.find_element(By.CSS_SELECTOR, "button.KGDocViewer_toolbar_button.js-home")
    ActionChains(driver).move_to_element(home_button).click(home_button).perform()


def get_all_pages(driver: WebDriver, issue_num: int, outdir: str = "",
                  overwrite_existing: bool = False) -> None:
    """When viewing a particular issue, this downloads all the
    pages to local files."""
    page_list = driver.find_elements(By.CLASS_NAME, "KGDocViewer_page")

    all_urls = {}
    all_pages_source = []
    issue_dir = f"Issue {str(issue_num).zfill(2)}"

    # here we want to cycle through each page, and download the
    # content of the iframe; however, the content is only loaded
    # when it is the current or next/previous page, so we need to
    # click the "next" arrow first and let the page load
    arrows = driver.find_element(By.CLASS_NAME, "KGDocViewer_arrows")
    for i, page in enumerate(page_list):
        time.sleep(0.5)
        iframe = page.find_element(By.TAG_NAME, "iframe")
        iframe = WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it(iframe))
        # driver.switch_to.frame(iframe)

        all_pages_source.append(driver.page_source)
        all_urls[driver.current_url] = i

        driver.switch_to.parent_frame()

        try:
            forward_button = arrows.find_element(By.CLASS_NAME, "KGDocViewer_pages_arrowsNext")
            forward_button.click()
        except NoSuchElementException:
            # we've reached the last page
            break

    # now that we have all the page sources, we can localize them,
    # in a context where we know all the URLs for the issue as well
    localizer = Localizer(root_dir=outdir, issue_dir=issue_dir, common_assets_dir="common", domain="https://dnd.dragonmag.com", issue_urls=all_urls, overwrite_assets=overwrite_existing)
    for i, source in enumerate(all_pages_source):
        start_time = time.time()
        filename = f"page{i+1}.html"
        converted = localizer.localize_page(source, filename, page=i+1)

        os.makedirs(os.path.join(outdir, issue_dir), exist_ok=True)
        with open(os.path.join(outdir, issue_dir, filename), "w") as f:
            f.write(converted)
        print(f"Page {i+1} finished: {(time.time() - start_time):.2f}s")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download issues of Dragon+ magazine.")
    parser.add_argument("-i", "--issue", nargs="+", type=int,
                        help="Issue numbers to download. Separate the numbers in the list with spaces. If flag is not set, will download all issues that are not in the outdir.")
    parser.add_argument("-o", "--outdir", nargs="?", default="./data",
                        help="Directory to place output files.")
    parser.add_argument("--overwrite", action="store_true",
                        help="Add this flag to overwrite existing styles, scripts, and images that have been downloaded previously.")
    parser.add_argument("-d", "--driver", nargs="?", default="firefox",
                        help=f"Which web driver to use. Choose from: {', '.join(DRIVER_OPTIONS)}")
    args = parser.parse_args()

    # find existing issues we already have in the outdir
    subdirs = [o for o in os.listdir(args.outdir) if os.path.isdir(os.path.join(args.outdir, o))]
    existing_issues = []
    for d in subdirs:
        match = re.fullmatch(r".*Issue ([0-9]+)", d)
        if match:
            existing_issues.append(int(match.group(1)) - 1)

    driver = start_driver(args.driver)
    all_issues = get_issues_list(driver)

    if args.issue is not None:
        # change from 1-indexed to 0-indexed
        issues_to_get = [x - 1 for x in args.issue]
    else:
        issues_to_get = [x for x in range(len(all_issues)) if x not in existing_issues]

    for i, iss in enumerate(issues_to_get):
        print(f"Retrieving Issue {iss+1}")
        click_issue_button(driver, all_issues[iss])
        time.sleep(3)  # wait for page to load

        get_all_pages(driver, issue_num=iss + 1, outdir=args.outdir, overwrite_existing=args.overwrite)

        if i < len(issues_to_get) - 1:
            return_home(driver)
            time.sleep(1)

    # create/update the index page
    print("Creating index page...")
    issue_metadata = get_issue_metadata(driver)
    create_index(issue_metadata, args.outdir)

    driver.close()