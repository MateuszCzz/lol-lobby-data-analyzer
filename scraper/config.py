from dataclasses import dataclass
from pathlib import Path
from typing import List

DATA_DIR = Path("data_src")

CHAMPION_NAMES: List[str] = [
    "Aatrox","Ahri","Akali","Akshan","Alistar","Ambessa","Amumu","Anivia","Annie","Aphelios","Ashe","aurelionsol","Aurora","Azir","Bard","belveth","Blitzcrank","Brand","Braum","Briar","Caitlyn","Camille","Cassiopeia","chogath","Corki","Darius","Diana","drmundo","Draven","Ekko","Elise","Evelynn","Ezreal","Fiddlesticks","Fiora","Fizz","Galio","Gangplank","Garen","Gnar","Gragas","Graves","Gwen","Hecarim","Heimerdinger","Hwei","Illaoi","Irelia","Ivern","Janna","jarvaniv","Jax","Jayce","Jhin","Jinx","ksante","kaisa","Kalista","Karma","Karthus","Kassadin","Katarina","Kayle","Kayn","Kennen","khazix","Kindred","Kled","kogmaw","LeBlanc","leesin","Leona","Lillia","Lissandra","Lucian","Lulu","Lux","Malphite","Malzahar","Maokai","masteryi","Mel","Milio","missfortune","Mordekaiser","Morgana","Naafiri","Nami","Nasus","Nautilus","Neeko","Nidalee","Nilah","Nocturne","Nunu","Olaf","Orianna","Ornn","Pantheon","Poppy","Pyke","Qiyana","Quinn","Rakan","Rammus","reksai","Rell","Renata","Renekton","Rengar","Riven","Rumble","Ryze","Samira","Sejuani","Senna","Seraphine","Sett","Shaco","Shen","Shyvana","Singed","Sion","Sivir","Skarner","Smolder","Sona","Soraka","Swain","Sylas","Syndra","tahmkench","Taliyah","Talon","Taric","Teemo","Thresh","Tristana","Trundle","Tryndamere","twistedfate","Twitch","Udyr","Urgot","Varus","Vayne","Veigar","velkoz","Vex","Vi","Viego","Viktor","Vladimir","Volibear","Warwick","Wukong","Xayah","Xerath","xinzhao","Yasuo","Yone","Yorick","Yunara","Yuumi","Zaahen","Zac","Zed","Zeri","Ziggs","Zilean","Zoe","Zyra"
]

LANES: List[str] = [
    "top", "jungle", "middle", "bottom", "support"
    ]


@dataclass(slots=True)
class ScrapeConfig:
    tier: str = "diamond_plus"
    min_pick_rate: float = 0.5
    scroll_iterations: int = 6