#!/usr/bin/env python3

import os
import time
from typing import List

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from localize import Localizer


def get_issues_list(driver: WebDriver) -> List[WebElement]:
    """From the main page, get the list of issues."""
    driver.get("https://dnd.dragonmag.com")
    time.sleep(1)

    issue_list = driver.find_element(By.CLASS_NAME, "KGDocPicker_editionsList")
    issues = issue_list.find_elements(By.TAG_NAME, "li")
    # for i in issues:
    #     print(i.text)

    return issues


def click_issue_button(driver: WebDriver, issue_elem: WebElement) -> None:
    """Given an issue, this finds the button and clicks it."""
    issue_button = issue_elem.find_element(By.TAG_NAME, "button")
    driver.execute_script("arguments[0].scrollIntoView();", issue_button)
    visible_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(issue_button))
    visible_button.click()


# def get_page(driver: WebDriver, filename: str = "",
#              root_dir: str = "", issue_dir: str = "",
#              common_assets_dir: str = "") -> None:
#     """Within the context of an iframe, this downloads the content
#     of the page to a local file."""
#     localizer = Localizer(root_dir=root_dir, issue_dir=issue_dir, common_assets_dir=common_assets_dir)
#     converted = localizer.localize_page(driver.page_source, filename)

#     os.makedirs(os.path.join(root_dir, issue_dir), exist_ok=True)
#     with open(os.path.join(root_dir, issue_dir, filename), "w") as f:
#         f.write(converted)


def get_all_pages(driver: WebDriver, issue_num: int, outdir: str = "") -> None:
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
        iframe = page.find_element(By.TAG_NAME, "iframe")
        iframe = WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it(iframe))
        # driver.switch_to.frame(iframe)

        all_pages_source.append(driver.page_source)
        all_urls[driver.current_url] = i

        # get_page(
        #     driver,
        #     filename=f"page{i+1}.html",
        #     root_dir=outdir,
        #     issue_dir=issue_dir,
        #     common_assets_dir="common"
        # )
        driver.switch_to.parent_frame()

        try:
            forward_button = arrows.find_element(By.CLASS_NAME, "KGDocViewer_pages_arrowsNext")
            forward_button.click()
            # time.sleep(1)
        except NoSuchElementException:
            # we've reached the last page
            break

    # now that we have all the page sources, we can localize them,
    # in a context where we know all the URLs for the issue as well
    for i, source in enumerate(all_pages_source):
        filename = f"page{i+1}.html"
        localizer = Localizer(root_dir=outdir, issue_dir=issue_dir, common_assets_dir="common", issue_urls=all_urls)
        converted = localizer.localize_page(source, filename)

        os.makedirs(os.path.join(outdir, issue_dir), exist_ok=True)
        with open(os.path.join(outdir, issue_dir, filename), "w") as f:
            f.write(converted)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download issues of Dragon+ magazine.")
    parser.add_argument("-i", "--issue", nargs="+", type=int,
                        help="Issue numbers to download. Separate the list with spaces. If flag is not set, will download all issues.")
    parser.add_argument("-o", "--outdir", nargs="?", default="./data",
                        help="Directory to place output files.")
    args = parser.parse_args()

    if args.issue is not None:
        # TODO: handle issue numbers here; need to return back to
        # main page in between
        pass

    driver = webdriver.Firefox()
    issues = get_issues_list(driver)

    click_issue_button(driver, issues[-1])
    time.sleep(3)  # wait for page to load

    get_all_pages(driver, issue_num=1, outdir=args.outdir)

    driver.close()