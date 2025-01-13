# League of Legends Real-Time Lobby Analysis

A Python based data-driven tool that collects and processes champion statistics from [LoLalytics](https://lolalytics.com), then queries the resulting datasets in real time during champion select to provide assistance in selecting optimal choices based on actions of the opposite players.

## Pipeline

**Stage 1 — Data Collection**

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Configure** (optional)

Open `config.py` to tune data collection parameters - tier bracket, minimum sample size, pick rate thresholds. Tighter filters may reduce noise by dropping matchups with insufficient game volume, at the cost of excluding more niche information.

**3. Run the collector**
```bash
python main.py [workers]
```

Crawls LoLalytics across every champion and role combination, extracting and caching relevant information such as per-matchup win rates, game counts, and pick rates into local JSON datasets. The *optional* `workers` parameter controls the number of parallel browser instances - scale up to reduce collection time at the cost of higher resource consumption. Defaults to 1.

---

**Stage 2 — Live Draft Analysis**

**4. Start the query engine**
```bash
python lobby_manager.py
```

**5. Feed picks as they happen**

Enter enemy champions as they lock in. The engine queries the dataset on each input, aggregating matchup statistics across all known enemies to rank available picks by weighted win rate advantage.