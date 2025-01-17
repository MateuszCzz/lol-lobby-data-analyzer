import time
from typing import Dict
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from config import ScrapeConfig, LANES
from scraper.parser import parse_item
from config import CHAMPION_NAMES
from scraper.driver import create_driver

LANE_DIV_INDICES = [2, 3, 4, 5, 6]
LANE_MAP = dict(zip(LANE_DIV_INDICES, LANES))
LABEL_XPATH_TPL = "/html/body/main/div[6]/div[1]/div[{i}]/div[2]"
NOT_FOUND_LOCATOR = (By.XPATH, "//main//span[contains(text(),'Resource Not Found')]")

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


def get_champion_games(driver) -> int | None:
    try:
        element = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//div[contains(text(),'Games')]/preceding-sibling::div[contains(@class,'font-bold')]",
                )
            )
        )
        return int(element.text.replace(",", ""))
    except Exception:
        return None


def scroll_page(driver):
    body = driver.find_element(By.CSS_SELECTOR, "body")
    for _ in range(3):
        body.send_keys(Keys.PAGE_DOWN)
        time.sleep(0.2)

def wait_for_page(driver, tag: str) -> bool:
    """Returns True if data is present, False if Resource Not Found page detected. Waits indefinitely."""
    first_block = (By.XPATH, LABEL_XPATH_TPL.format(i=LANE_DIV_INDICES[0]))
    try:
        WebDriverWait(driver, 0.1).until(
            EC.any_of(
                EC.presence_of_element_located(first_block),
                EC.presence_of_element_located(NOT_FOUND_LOCATOR),
            )
        )
    except Exception:
        print(f"{tag} Timed out waiting for page")
        return False

    if driver.find_elements(*NOT_FOUND_LOCATOR):
        print(f"{tag} Skipped — Resource Not Found")
        return False

    print(f"{tag} Data found — proceeding to scrape")
    return True


def scrape_block(driver, block_xpath: str, config: ScrapeConfig) -> Dict:
    block_data: Dict = {}
    try:
        parent = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, block_xpath))
        )
    except Exception:
        return block_data

    for _ in range(config.scroll_iterations):
        children = driver.find_elements(By.XPATH, f"{block_xpath}/div[1]/*")
        for element in children:
            item = parse_item(element)
            name = item["name"]
            try:
                if int(item.get("games", 0)) < config.min_games:
                    continue
            except (ValueError, TypeError):
                continue

            if name not in ("error", "N/A") and name not in block_data:
                block_data[name] = item

        driver.execute_script("arguments[0].scrollLeft += 550;", parent)
        time.sleep(0.5)

    return block_data

def scrape_champion(driver, champion: str, lane: str, config: ScrapeConfig) -> Dict | None:
    tag = f"[{champion}/{lane}]"
    driver.get(build_url(champion, lane, config.tier))
    scroll_page(driver)
    if not wait_for_page(driver, tag):
        return None

    if config.min_pick_rate > 0:
        pick_rate = get_pick_rate(driver)
        if pick_rate is None:
            print(f"{tag} Skipped — pick rate could not be read")
            return None
        if pick_rate < config.min_pick_rate:
            print(f"{tag} Skipped — pick rate {pick_rate}% below minimum {config.min_pick_rate}%")
            return None

    if config.min_champion_games  > 0:
        champion_games = get_champion_games(driver)
        if champion_games is None:
            print(f"{tag} Skipped — champion games could not be read")
            return None
        if champion_games < config.min_champion_games:
            print(f"{tag} Skipped — champion games {champion_games} below minimum {config.min_champion_games}")
            return None
    
    all_data: Dict = {}

    for i in LANE_DIV_INDICES:
        block_xpath = LABEL_XPATH_TPL.format(i=i)
        opp_lane = LANE_MAP[i]
        block_data = scrape_block(driver, block_xpath, config)

        if not block_data:
            print(f"{tag} Block div[{i}] ({opp_lane}) — no items found, skipping")
            continue

        for item in block_data.values():
            item["opponent_lane"] = opp_lane

        all_data.update(block_data)
        print(f"{tag} Block div[{i}] ({opp_lane}) — {len(block_data)} matchups scraped")

    return all_data if all_data else None

def scrape_play_rates(config: ScrapeConfig) -> dict:
    driver = create_driver()
    results: dict = {}

    try:
        for champion in CHAMPION_NAMES:
            results[champion] = {}
            for lane in LANES:
                tag = f"[play_rates/{champion}/{lane}]"
                try:
                    driver.get(build_url(champion, lane, config.tier))

                    if driver.find_elements(*NOT_FOUND_LOCATOR):
                        print(f"{tag} Not Found — writing 0")
                        results[champion][lane] = 0
                        continue

                    pick_rate = get_pick_rate(driver)
                    results[champion][lane] = pick_rate or 0
                    print(f"{tag} {results[champion][lane]}%")

                except Exception as e:
                    print(f"{tag} Error ({e}) — writing 0")
                    results[champion][lane] = 0

            # Normalize to 100%
            total = sum(results[champion].values())
            if total > 0:
                results[champion] = {
                    lane: round(rate / total * 100, 2)
                    for lane, rate in results[champion].items()
                }
    finally:
        driver.quit()

    return results