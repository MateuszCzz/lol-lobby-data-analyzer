import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import CHAMPION_NAMES, LANES, DATA_DIR, ScrapeConfig, PLAY_RATES_FILE
from scraper.driver import create_driver
from scraper.collector import scrape_champion, scrape_play_rates
from scraper.storage import ensure_data_dir, save_json, load_completed_champions

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

def play_rate_scrape(cfg: ScrapeConfig) -> None:
    completed, data = load_completed_champions(PLAY_RATES_FILE)
 
    if completed == set(CHAMPION_NAMES):
        print("Play rates already complete - skipping")
        return
 
    if completed:
        print(f"Resuming play rates — {len(completed)}/{len(CHAMPION_NAMES)} already done")
    else:
        print("Starting play rate scrape")

    # filtering out done champions    
    pending = [c for c in CHAMPION_NAMES if c not in completed]
    chunks = chunk_tasks(pending, cfg.play_rate_chunks)
    print(f"{len(pending)} champions pending - {len(chunks)} chunks of {len(chunks[0])} each\n")
 
    driver = create_driver()
    try:
        for idx, chunk in enumerate(chunks):
            print(f"Chunk {idx + 1}/{len(chunks)}: {', '.join(chunk)}")
            chunk_results = scrape_play_rates(driver, chunk, cfg)
 
            data.update(chunk_results)
            completed.update(chunk)
            data["_completed"] = sorted(completed)
            save_json(PLAY_RATES_FILE, data)
            print(f"Chunk {idx + 1} saved — {len(completed)}/{len(CHAMPION_NAMES)} champions done\n")
    finally:
        driver.quit()
 
    print(f"Play rates complete → {PLAY_RATES_FILE}")

def main(workers: int):
    ensure_data_dir(DATA_DIR)
    config = ScrapeConfig()
    play_rate_scrape(config)

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