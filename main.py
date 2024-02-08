import re
import time
import logging
import requests
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import ElementClickInterceptedException

logging.basicConfig(filename="logging.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

URL = "https://afitower.ru/?sort=price&sortBy=asc&square%5B%5D=20&square%5B%5D=116&stock=all&floor%5B%5D=2&floor%5B%5D=50&price%5B%5D=11&price%5B%5D=45&numberFlat=&pageView=params&view=all&page=1&offset=0&showMore=true"


def main():
    # Логирование о начале работы парсера
    logging.info("Начало работы парсера")

    links = get_links()
    data = get_data(links)
    save_to_excel(data)

    # Логирование о завершении работы парсера
    logging.info("Парсер успешно завершил работу")


def get_links():
    # Инициализация веб-драйвера
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.get(URL)

    links = set()
    index = 14

    while True:
        try:
            # Ожидание появления кнопки "button_inline"
            wait = WebDriverWait(driver, 5)
            time.sleep(3)
            buttons = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "button_inline")))

            if index < len(buttons):
                # Нажатие кнопки для загрузки дополнительных ссылок
                action_chains = ActionChains(driver)
                action_chains.move_to_element(buttons[index]).perform()
                time.sleep(3)
                buttons[index].click()
                time.sleep(5)

                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "room-preview")))

                room_preview_links = driver.find_elements(By.CLASS_NAME, "room-preview")
                for link in room_preview_links:
                    if link.get_attribute("href") not in links:
                        links.add(link.get_attribute("href"))
                        logging.info(f"Получена ссылка: {link.get_attribute('href')}")
                index += 7
                logging.info("Переход к следующей странице")
            else:
                break

        except ElementClickInterceptedException:
            break

    driver.quit()

    logging.info("Собраны все ссылки")
    logging.info(f"Общее количество собранных ссылок: {len(links)}")

    return links


def get_data(links):
    data = []

    for i, link in enumerate(links, start=1):
        response = requests.get(link)
        soup = BeautifulSoup(response.text, "html.parser")
        room_params = soup.find_all(class_="room-params__value")

        section, floor, price_element_index = extract_section_floor_and_price_index(room_params)

        price, sale_price = extract_prices(room_params, price_element_index)

        data.append({
            "complex": "Afi Tower",
            "faza": None,
            "building": 1,
            "section": section,
            "floor": floor,
            "floor_number": None,
            "number": soup.find(class_="room__title").text.strip(),
            "rooms": extract_room_number(room_params[1].text),
            "area": room_params[0].text.replace(" м²", ""),
            "area_living": None,
            "area_kitchen": None,
            "price": int(price.replace(" ", "").replace("₽", "")),
            "price_sale": int(sale_price.replace(" ", "").replace("₽", "")),
            "furnished": room_params[2].text,
            "is_furniture": None,
            "type": None,
            "plan": None,
            "source": link,
            "deadline": None,
        })

        logging.info(f"Обработано страниц {i}/{len(links)}")

    return data


def extract_section_floor_and_price_index(room_params):
    if room_params[5].text.lower().strip() not in ["а", "б"]:
        section = room_params[6].text
        floor = room_params[5].text
        price_element_index = 7
    else:
        section = room_params[5].text
        floor = room_params[4].text
        price_element_index = 6

    return section, floor, price_element_index


def extract_prices(room_params, index):
    price_element = room_params[index]
    sale_price_element = price_element.find("div")

    if sale_price_element:
        return sale_price_element.text.strip(), price_element.find("span").text.strip()
    else:
        return price_element.text.strip(), None


def extract_room_number(text):
    return "1c" if "Студия" in text else re.search(r"\b(\d+)-?комнатная\b", text).group(1) if re.search(
        r"\b(\d+)-?комнатная\b", text) else None


def save_to_excel(data):
    df = pd.DataFrame(data)
    df.to_excel("result.xlsx", index=False)


if __name__ == "__main__":
    main()
