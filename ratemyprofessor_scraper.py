from time import sleep
from parsel import Selector
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from selenium.webdriver.common.action_chains import ActionChains
import json

print("Scraper Started...")


# helper function for getting values from selector object
def parse(response, xpath, get_method="get", comma_join=False, space_join=True):
    """_This function is used to get values from selector object by using xpath expressions_

    Args:
        response (_scrapy.Selector_): _A selector object on which we can use xpath expressions_
        xpath_str (_str_): _xpath expression to be used_
        get_method (str, optional): _whether to get first element or all elements_. Defaults to "get".
        comma_join (bool, optional): _if we are getting all elements whether to join on comma or not_. Defaults to False.
        space_join (bool, optional): _if we are getting all elements whether to join on space or not_. Defaults to False.

    Returns:
        _str_: _resultant value of using xpath expression on the scrapy.Selector object_
    """
    value = ""
    if get_method == "get":
        value = response.xpath(xpath).get()
        value = (value or "").strip()
    elif get_method == "getall":
        value = response.xpath(xpath).getall()
        if value:
            if comma_join:
                value = " ".join(
                    ", ".join([str(x).strip() for x in value]).split()
                ).strip()
                value = (value or "").strip()
            elif space_join:
                value = " ".join(
                    " ".join([str(x).strip() for x in value]).split()
                ).strip()
                value = (value or "").strip()
        else:
            value = ""
    return value


# this function is used to setup the bot
def bot_setup(headless=False):
    """_This function is used to setup the bot_

    Args:
        proxy_switch (_int_): _whether to use proxy or not, 0 means yes, and 1 means no_
        headless (bool, optional): _whether to run the bot in headless mode or not_. Defaults to False.

    Returns:
        _selenium.webdriver_: _returns a selenium.webdriver object to be used_
    """

    # options to be used
    options = webdriver.ChromeOptions()
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_argument("force-device-scale-factor=0.7")
    # if headless==True, make the bot headless
    if headless:
        options.add_argument("--headless=new")

    driver = webdriver.Chrome(
        service=Service(),
        options=options,
    )
    # setup implicit wait
    driver.implicitly_wait(3)
    driver.maximize_window()
    return driver


# to click a button
def click_btn(driver, xpath, wait_time=5):
    btn = WebDriverWait(driver, wait_time).until(
        EC.presence_of_element_located((By.XPATH, xpath))
    )
    ActionChains(driver).move_to_element(btn).perform()
    sleep(1)
    ActionChains(driver).click(btn).perform()


# wait for an element to be present on the screen
def wait_for_element(driver, xpath, wait_time=5):
    WebDriverWait(driver, wait_time).until(
        EC.presence_of_element_located((By.XPATH, xpath))
    )


# check if the driver is alive or not
def is_driver_alive(driver):
    try:
        # Attempt to interact with the driver
        driver.title
        return True
    except:
        return False


# read the input data
df = pd.read_csv("input.csv")
input_data = df.to_dict("records")
# setup the bot
driver = bot_setup()
# go to the ratemyprofessor website
driver.get(input_data[0]["School Professors URL"])
sleep(2)
# close the pop-up
click_btn(driver, xpath='//button[text()="Close"]')
sleep(2)

records = []
# loop through the input data
for inp_data_idx, inp_data in enumerate(input_data):
    # get the university name and url
    university_name = inp_data["School Name"]
    university_url = inp_data["School Professors URL"]
    driver.get(university_url)
    # infinite loop to load all the professors
    while True:
        # wait for the professors to load
        wait_for_element(
            driver, xpath='//a[contains(@class,"TeacherCard__StyledTeacherCard")]'
        )
        # get the response
        response = Selector(text=driver.page_source)
        # get the professor urls
        temp_urls = parse(
            response,
            xpath='//a[contains(@class,"TeacherCard__StyledTeacherCard")]/@href',
            get_method="getall",
            space_join=False,
        )
        temp_urls = ["https://www.ratemyprofessors.com" + x for x in temp_urls]
        # add the professor urls to the records
        for temp_url in temp_urls:
            rec = {"university_name": university_name, "professor_url": temp_url}
            if rec not in records:
                records.append(rec)
        # get the total number of urls
        total_urls = parse(
            response,
            xpath='//h1[@data-testid="pagination-header-main-results"]/text()[1]',
        )
        # get the total number of urls loaded
        total_urls_loaded = len(temp_urls)
        # print the progress
        print(
            "University URL -> {}/{} | URLs Loaded -> {}/{}".format(
                inp_data_idx + 1, len(input_data), total_urls_loaded, total_urls
            )
        )
        # check if there is a next page
        is_next_page = parse(response, xpath='//button[text()="Show More"]')
        if is_next_page:  # if there is a next page, click the show more button
            click_btn(driver, xpath='//button[text()="Show More"]')
            while True:
                response = Selector(text=driver.page_source)
                is_loading = parse(response, xpath='//button[contains(., "Loading")]')
                if is_loading:
                    sleep(1)
                    continue
                else:
                    break
        else:
            break
    # get the response
    response = Selector(text=driver.page_source)
    # get the professor urls
    temp_urls = parse(
        response,
        xpath='//a[contains(@class,"TeacherCard__StyledTeacherCard")]/@href',
        get_method="getall",
        space_join=False,
    )
    temp_urls = ["https://www.ratemyprofessors.com" + x for x in temp_urls]
    # add the professor urls to the records
    for temp_url in temp_urls:
        records.append({"university_name": university_name, "professor_url": temp_url})


results = []
# loop through the records
for rec_idx, rec in enumerate(records):
    # get the professor url and school name
    professor_url = rec["professor_url"]
    professor_school = rec["university_name"]
    # loop to try 3 times
    for _ in range(3):
        try:
            # try to get the professor page
            try:
                driver.get(professor_url)
                wait_for_element(
                    driver, xpath='//div[contains(@class,"NameTitle__Name")]'
                )
                sleep(0.5)
            except:
                break
            # save the response
            response = Selector(text=driver.page_source)
            # get the professor details
            items = {}
            items["professor_url"] = professor_url
            items["professor_school"] = professor_school

            items["Professor Name"] = parse(
                response,
                xpath='//div[contains(@class,"NameTitle__Name")]//text()',
                get_method="getall",
            )
            items["School"] = parse(
                response,
                xpath='//div[contains(@class,"NameTitle__Title")]/a[contains(@href, "school")]/text()',
                get_method="getall",
            )
            items["Departement"] = parse(
                response,
                xpath='//div[contains(@class,"NameTitle__Title")]//a[contains(@class, "TeacherDepartment")]//text()',
                get_method="getall",
            )
            items["Overall Rating"] = parse(
                response,
                xpath='//div[contains(@class,"RatingValue__Numerator")]/text()',
            )
            items["Total Reviews"] = (
                parse(
                    response,
                    xpath='//a[@href="#ratingsList"]/text()',
                    get_method="getall",
                )
                .replace("ratings", "")
                .strip()
            )

            # get the rating distribution

            try:
                script_text = parse(
                    response,
                    xpath='//script[contains(text(), "window.__RELAY_STORE__")]/text()',
                )
                script_text = script_text.replace(
                    "window.__RELAY_STORE__ = ", ""
                ).strip()
                script_text = script_text.split("};")[0].strip() + "}"

                script_json = json.loads(script_text)
                json_keys = list(script_json.keys())
                rating_distribution_key = [
                    x for x in json_keys if ":ratingsDistribution" in x
                ][0]
                items["5 Star Reviews"] = script_json.get(
                    rating_distribution_key, ""
                ).get("r5", "")
                items["4 Star Reviews"] = script_json.get(
                    rating_distribution_key, ""
                ).get("r4", "")
                items["3 Star Reviews"] = script_json.get(
                    rating_distribution_key, ""
                ).get("r3", "")
                items["2 Star Reviews"] = script_json.get(
                    rating_distribution_key, ""
                ).get("r2", "")
                items["1 Star Reviews"] = script_json.get(
                    rating_distribution_key, ""
                ).get("r1", "")

            except:
                items["5 Star Reviews"] = ""
                items["4 Star Reviews"] = ""
                items["3 Star Reviews"] = ""
                items["2 Star Reviews"] = ""
                items["1 Star Reviews"] = ""
            # save the data
            results.append(items)
            df = pd.DataFrame(results)
            df.to_csv("results_ratemyprofessor.csv", index=False, encoding="utf-8-sig")
            # print the progress
            print("Professors Done -> {}/{}".format(rec_idx + 1, len(records)))
            break
        except:  # if there is an error, continue
            continue
    else:  # if retry fails 3 times then close the driver and open a new one
        if is_driver_alive(driver):
            driver.close()
            driver.quit()
            sleep(2)
        driver = bot_setup()
        sleep(1)
        driver.get(input_data[0]["School Professors URL"])
        sleep(2)
        click_btn(driver, xpath='//button[text()="Close"]')
        sleep(2)

if is_driver_alive(driver):
    driver.close()
    driver.quit()

print("Scraper Finished...")
