from selenium.webdriver import Firefox
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager

def create_driver(headless: bool = True) -> Firefox:
    options = Options()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--width=1920")
    options.add_argument("--height=1080")

    service = FirefoxService(GeckoDriverManager().install())
    return Firefox(service=service, options=options)