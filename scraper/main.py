import argparse
from pathlib import Path

from config import CHAMPION_NAMES, LANES, DATA_DIR, ScrapeConfig
from driver import create_driver
from collector import scrape_champion
from storage import ensure_data_dir, save_json


def split_champions(part: int):
    size = len(CHAMPION_NAMES) // 5
    start = part * size
    if part == 4:
        return CHAMPION_NAMES[start:]
    return CHAMPION_NAMES[start:start + size]


def run_subset(driver, champions, config: ScrapeConfig):
    for champion in champions:
        for lane in LANES:
            file_path = DATA_DIR / f"{champion}_{lane}.json"

            if file_path.exists():
                continue

            data = scrape_champion(driver, champion, lane, config)

            if data:
                save_json(file_path, data)


def main(part: int):
    ensure_data_dir(DATA_DIR)
    config = ScrapeConfig()

    driver = create_driver()

    try:
        if part == 0:
            champions = CHAMPION_NAMES
        else:
            champions = split_champions(part - 1)

        run_subset(driver, champions, config)
    finally:
        driver.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("part", type=int, choices=range(6))
    args = parser.parse_args()

    main(args.part)