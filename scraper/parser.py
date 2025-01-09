from selenium.webdriver.common.by import By


def parse_item(element) -> dict:
    text = element.text.replace("\n", " ").strip().split()

    images = element.find_elements(By.TAG_NAME, "img")
    name = images[0].get_attribute("alt") if images else "error"

    try:
        win_rate = text[0]
        win_rate_value = float(win_rate.replace("%", ""))
        win_rate_diff = round(win_rate_value - 50, 2)
    except (IndexError, ValueError):
        win_rate = "N/A"
        win_rate_diff = "N/A"

    return {
        "name": name,
        "win_rate": win_rate,
        "popularity": text[3] if len(text) >= 5 else "N/A",
        "games": text[4] if len(text) >= 5 else "N/A",
        "win_rate_diff": win_rate_diff,
    }