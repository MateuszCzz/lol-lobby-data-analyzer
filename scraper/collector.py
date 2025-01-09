import time
from pathlib import Path
from typing import Dict

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

from config import LANES, ScrapeConfig
from parser import parse_item


def build_url(champion: str, lane: str, tier: str) -> str:
    return f"https://lolalytics.com/lol/{champion.lower()}/build/?lane={lane}&tier={tier}"


def get_pick_rate(driver) -> float | None:
    try:
        element = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//div[contains(text(),'Pick Rate')]/preceding-sibling::div[contains(@class,'font-bold')]",
                )
            )
        )
        return float(element.text.strip("%"))
    except Exception:
        return None


def scroll_page(driver):
    body = driver.find_element(By.CSS_SELECTOR, "body")
    for _ in range(3):
        body.send_keys(Keys.PAGE_DOWN)
        time.sleep(0.25)


def scrape_lane(driver, lane: str, config: ScrapeConfig) -> Dict:
    lane_data = {}

    xpath = f"/html/body/main/div[6]/div[1]/div[2]/div[2]"
    parent = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.XPATH, xpath))
    )

    for _ in range(config.scroll_iterations):
        children = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, f"{xpath}/div[1]/*"))
        )

        for element in children:
            item = parse_item(element)
            name = item["name"]

            if name not in ("error", "N/A") and name not in lane_data:
                lane_data[name] = item

        driver.execute_script("arguments[0].scrollLeft += 500;", parent)
        time.sleep(0.5)

    return lane_data


def scrape_champion(driver, champion: str, lane: str, config: ScrapeConfig):
    url = build_url(champion, lane, config.tier)
    driver.get(url)

    scroll_page(driver)

    pick_rate = get_pick_rate(driver)
    if pick_rate is None or pick_rate < config.min_pick_rate:
        return None

    return scrape_lane(driver, lane, config)