#!/usr/bin/env python3

import os
import time

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

driver = webdriver.Firefox()
driver.get("https://dnd.dragonmag.com")

time.sleep(1)

issue_list = driver.find_element(By.CLASS_NAME, "KGDocPicker_editionsList")
issues = issue_list.find_elements(By.TAG_NAME, "li")
# for i in issues:
#     print(i.text)

first_issue_button = issues[-1].find_element(By.TAG_NAME, "button")

driver.execute_script("arguments[0].scrollIntoView();", first_issue_button)
visible_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(first_issue_button))
visible_button.click()

time.sleep(3)

page_list = driver.find_elements(By.CLASS_NAME, "KGDocViewer_page")

# here we want to cycle through each page, and download the content of the iframe;
# however, the content is only loaded when it is the current or next/previous page, so we need to
# click the "next" arrow first and let the page load
arrows = driver.find_element(By.CLASS_NAME, "KGDocViewer_arrows")
for i, page in enumerate(page_list):
    iframe = page.find_element(By.TAG_NAME, "iframe")
    iframe = WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it(iframe))
    # driver.switch_to.frame(iframe)

    with open(f"page{i+1}.html", "w") as f:
        f.write(driver.page_source)
    
    driver.switch_to.parent_frame()

    try:
        forward_button = arrows.find_element(By.CLASS_NAME, "KGDocViewer_pages_arrowsNext")
        forward_button.click()
        # time.sleep(1)
    except NoSuchElementException:
        # we've reached the last page
        break

time.sleep(5)
driver.close()
