import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import CHAMPION_NAMES, LANES, DATA_DIR, ScrapeConfig, PLAY_RATES_FILE
from scraper.driver import create_driver
from scraper.collector import scrape_champion, scrape_play_rates
from scraper.storage import ensure_data_dir, save_json

def get_pending_tasks() -> list[tuple[str, str]]:
    return [
        (champion, lane)
        for champion in CHAMPION_NAMES
        for lane in LANES
        if not (DATA_DIR / f"{champion}_{lane}.json").exists()
    ]

def log(worker_id: int, message: str):
    print(f"[Worker {worker_id}] {message}")

def worker(worker_id: int, tasks: list[tuple[str, str]], config: ScrapeConfig):
    driver = create_driver()
    try:
        for champion, lane in tasks:
            file_path = DATA_DIR / f"{champion}_{lane}.json"
            if file_path.exists():
                log(worker_id, f"{champion}/{lane} — already exists, skipping")
                continue
            try:
                data = scrape_champion(driver, champion, lane, config)
                if data:
                    save_json(file_path, data)
                    log(worker_id, f"{champion}/{lane} — done ({len(data)} items)")
                else:
                    log(worker_id, f"{champion}/{lane} — no data returned")
            except Exception as e:
                log(worker_id, f"{champion}/{lane} — error: {e}")
    finally:
        driver.quit()
        log(worker_id, "finished all assigned tasks")

def chunk_tasks(tasks: list, n: int) -> list[list]:
    size = max(1, len(tasks) // n)
    chunks = [tasks[i:i + size] for i in range(0, len(tasks), size)]
    if len(chunks) > n:
        chunks[n - 1].extend(chunks.pop())
    return chunks

def main(workers: int):
    ensure_data_dir(DATA_DIR)
    config = ScrapeConfig()
    
    if PLAY_RATES_FILE.exists():
        print("000_play_rates.json already exists — skipping play rate scrape")
    else:
        print("Scraping play rates for all champions × lanes …")
        play_rates = scrape_play_rates(config)
        save_json(PLAY_RATES_FILE, play_rates)
        print(f"Play rates saved → {PLAY_RATES_FILE}")

    tasks = get_pending_tasks()
    if not tasks:
        print("Nothing to scrape — all files already exist")
        return

    # round up <1 to 1
    workers = max(1, min(workers, len(tasks)))

    print(f"Scraping {len(tasks)} combos across {workers} worker(s)")

    if workers == 1:
        # Skip thread pool entirely
        worker(0, tasks, config)
        return

    chunks = chunk_tasks(tasks, workers)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(worker, i, chunk, config): i for i, chunk in enumerate(chunks)}
        for future in as_completed(futures):
            i = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"[Worker {i}] crashed unexpectedly — {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("workers", type=int, default=1, nargs="?")
    args = parser.parse_args()
    main(args.workers)