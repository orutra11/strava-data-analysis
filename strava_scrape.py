import pandas as pd
import time
import re
import os
from dotenv import load_dotenv

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy import insert

from data_model import (
    Base,
    Athlete,
    Activity,
    Split,
)

load_dotenv()

ACT_BASE_URL = "https://www.strava.com/activities/"
SEGMENT_BASE_URL = "https://www.strava.com/segments/"
SEGMENT_EFFORT_BASE_URL = "https://www.strava.com/segment_efforts/"
ATHLETE_BASE_URL = "https://www.strava.com/athletes/"

login_url = "https://www.strava.com/login"
strava_email = os.getenv("STRAVA_LOGIN_EMAIL")
strava_password = os.getenv("STRAVA_LOGIN_PASSWORD")

postgres_ip = os.getenv("POSTGRES_SERVER_IP")
postgres_port = os.getenv("POSTGRES_SERVER_PORT")
postgres_user = os.getenv("POSTGRES_SERVER_USER")
postgres_pass = os.getenv("POSTGRES_SERVER_PASSWORD")

alchemy_engine = create_engine(
    f"postgresql+psycopg2://{postgres_user}:{postgres_pass}@{postgres_ip}:{postgres_port}/stravadb"
)


def selenium_webdriver():
    # WebDriver options
    webdriver_options = webdriver.ChromeOptions()
    webdriver_options.headless = True
    # webdriver_options.page_load_strategy = 'normal'
    webdriver_options.page_load_strategy = "eager"

    driver = webdriver.Chrome(
        service=Service(executable_path=ChromeDriverManager().install()),
        options=webdriver_options,
    )

    # Return objects
    return driver


def strava_login():
    # Load Selenium WebDriver
    if "driver" in vars():
        if driver.service.is_connectable() is True:
            pass

    else:
        driver = selenium_webdriver()

        # Open website
        driver.get(url=login_url)
        time.sleep(2)

        # Reject cookies
        try:
            driver.find_element(
                by=By.XPATH,
                value='.//button[@class="btn-deny-cookie-banner"]',
            ).click()

        except NoSuchElementException:
            pass

        # Login
        driver.find_element(by=By.ID, value="email").send_keys(strava_email)
        driver.find_element(by=By.ID, value="password").send_keys(strava_password)
        time.sleep(1)

        driver.find_element(by=By.XPATH, value='.//*[@type="submit"]').submit()

        # Return objects
        return driver


def get_segment_leaderboard(_driver, _segment_id, num_results=10):
    _driver.get(
        url=(SEGMENT_BASE_URL + _segment_id),
    )

    leaderboard = _driver.find_elements(By.XPATH, value='//div[@id="results"]')
    list_dfs = pd.read_html(leaderboard[0].get_attribute("innerHTML"))
    leaderboard_df = list_dfs[0]

    efforts = _driver.find_elements(
        By.XPATH,
        value='//div[@id="results"]//table//tr//td[@data-tracking-element="leaderboard_effort"]//a',
    )
    for _idx, _r in enumerate(efforts):
        link_to_effort = _r.get_attribute("href")
        leaderboard_df.loc[_idx, "link"] = link_to_effort

    return _driver, leaderboard_df


def get_activity_details_from_segment_effort(_driver, _segment_effort):
    effort_url = (
        _segment_effort
        if "segment_efforts" in _segment_effort
        else SEGMENT_EFFORT_BASE_URL + _segment_effort
    )
    _driver.get(
        url=(effort_url),
    )
    # time.sleep(3)

    current_url = _driver.current_url
    # url template: https://www.strava.com/activities/ACTIVITY_ID/segments/SEGMENT_EFFORT_ID
    # url template(2): https://www.strava.com/activities/ACTIVITY_ID#SEGMENT_EFFORT_ID
    url_re = "https:\/\/www\.strava\.com\/activities\/(\d+)\/segments\/(\d+)"
    z = re.match(url_re, current_url)

    if z is None:
        url_re = "https:\/\/www\.strava\.com\/activities\/(\d+)#(\d+)"
        z = re.match(url_re, current_url)

    act_id, effort_id = z.groups()

    # overview = _driver.find_element(By.XPATH, '//a[contains(@href, "overview")]')
    # overview.click()

    _driver.get(
        url=(f"{ACT_BASE_URL}/{act_id}/overview"),
    )

    table = _driver.find_elements(
        By.XPATH, value='//div[contains(@class, "mile-splits")]'
    )
    df_list = pd.read_html(table[0].get_attribute("innerHTML"))
    splits = df_list[0]

    # date XPATH: //div[@class="details-container"]//time
    activity_date = _driver.find_element(
        By.XPATH, '//div[@class="details-container"]//time'
    )

    # athlete XPATH: //section[@id="heading"]//header//a[contains(@href,"athletes")]
    athlete = _driver.find_element(
        By.XPATH, '//section[@id="heading"]//header//a[contains(@href,"athletes")]'
    )

    # href template: /athletes/ATHLETE_ID
    ath_id_re = "https:\/\/www.strava.com\/athletes\/(\d+)"
    z = re.match(ath_id_re, athlete.get_attribute("href"))
    ath_id = z.groups()[0]

    # distance XPATH: //section[@id="heading"]//div[contains(@class,"activity-stats")]//li[1]
    distance = _driver.find_element(
        By.XPATH,
        '//section[@id="heading"]//div[contains(@class,"activity-stats")]//li[1]',
    )
    dist_text = distance.text.split("\n")[0]

    dist_re = "(\d+\.\d+) .{2}"
    z = re.match(dist_re, dist_text.replace(",", "."))
    activity_distance = float(z.groups()[0])

    # total time XPATH: //section[@id="heading"]//div[contains(@class,"activity-stats")]//li[2]
    elapsed = _driver.find_element(
        By.XPATH,
        '//section[@id="heading"]//div[contains(@class,"activity-stats")]//li[2]',
    )
    elapsed_text = elapsed.text.split("\n")[0]

    # pace XPATH: //section[@id="heading"]//div[contains(@class,"activity-stats")]//li[3]
    pace = _driver.find_element(
        By.XPATH,
        '//section[@id="heading"]//div[contains(@class,"activity-stats")]//li[3]',
    )
    pace_re = "(\d+:\d{2}) \/(.{2})"
    z = re.match(pace_re, pace.text.split("\n")[0])
    pace_str, pace_units = z.groups()

    minutes, seconds = pace_str.split(":")
    pace_seconds = int(minutes) * 60 + int(seconds)

    activity_details = {
        "athlete_name": athlete.text,
        "athlete_id": ath_id,
        "activity_date": activity_date.text,
        "distance": activity_distance,
        "elapsed_time": elapsed_text,
        "pace": pace_seconds,
        "pace_unit": pace_units,
    }

    return _driver, activity_details, splits


def get_event_performances(_base_segment, _event_distance, _event_name):
    driver = strava_login()

    driver, leaderboard = get_segment_leaderboard(driver, _base_segment)
    details_list = []
    splits_list = []

    for _idx in range(len(leaderboard)):
        print(leaderboard.loc[_idx, "link"])
        driver, activity_details, splits_df = get_activity_details_from_segment_effort(
            driver, leaderboard.loc[_idx, "link"]
        )

        details_list.append(activity_details)
        splits_list.append(splits_df)

    driver.close()

    return leaderboard, details_list, splits_list


if __name__ == "__main__":
    # Base.metadata.create_all(alchemy_engine)
    l, d, s = get_event_performances("12444719", 21.1, "Mitja Gandia")
    # print(d)
    # print(s)
