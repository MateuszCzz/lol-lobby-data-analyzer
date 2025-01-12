import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import CHAMPION_NAMES, LANES, DATA_DIR, ScrapeConfig
from driver import create_driver
from collector import scrape_champion
from storage import ensure_data_dir, save_json

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

    tasks = get_pending_tasks()
    if not tasks:
        print("Nothing to scrape — all files already exist")
        return

    chunks = chunk_tasks(tasks, workers)
    print(f"Scraping {len(tasks)} combos across {workers} workers")

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
    parser.add_argument("workers", type=int, default=5, nargs="?")
    args = parser.parse_args()
    main(args.workers)