from selenium.webdriver import Firefox
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager


def create_driver() -> Firefox:
    service = FirefoxService(GeckoDriverManager().install())
    return Firefox(service=service)