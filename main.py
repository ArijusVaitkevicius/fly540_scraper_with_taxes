import os
import re
from datetime import date, timedelta, datetime, timezone
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from multiprocessing import Pool, cpu_count
import pandas as pd
import logging as logs

# Chrome driver and chrome settings.
CHROME_PATH = 'C:/Program Files/Google/Chrome/Application/chrome.exe'  # Specify the path to chrome.exe.
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("start-maximized")
prefs = {"profile.managed_default_content_settings.images": 2}
chrome_options.add_experimental_option("prefs", prefs)
chrome_options.binary_location = CHROME_PATH

# If you're using a proxy server comment these two lines
s = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=s, options=chrome_options)

# If you're using a proxy server uncomment these two lines
# DRIVER_PATH = '/path/to/chromedriver'
# driver = webdriver.Chrome(executable_path=DRIVER_PATH, options=chrome_options)

driver.implicitly_wait(10)


def log(level, message):
    """
    This function configures logging settings.

    :param str level: log level
    :param str message: log message
    :return: None
    """
    logs.basicConfig(level=logs.INFO, filename='fly540.log', filemode="a",
                     format='%(asctime)s | %(levelname)s | %(message)s', datefmt='%Y %m %d %H:%M:%S', force=True)
    if level == 'INFO':
        logs.info(f'{message}')
    if level == 'WARNING':
        logs.warning(f'{message}')
    if level == 'ERROR':
        logs.error(f'{message}')


def flights_scraper(dep_iata, arr_iata, cur, dep_date, ret_date):
    """
    This function generates URL by giving arguments.
    Gets page html source code and counts all possible flight combinations and returns their indexes.

    :param str dep_iata: Departure flight IATA airport code
    :param str arr_iata: Arrival flight IATA airport code
    :param str cur: Currency
    :param datetime.date dep_date: Departing date
    :param datetime.date ret_date: Returning date
    :return: list of url and flights indexes
    """

    # List to return.
    url_with_indexes = []

    # Generates URL by variables.
    url = f"https://www.fly540.com/flights/?isoneway=0&depairportcode={dep_iata}" \
          f"&arrvairportcode={arr_iata}&date_from={dep_date.strftime('%a')}%2C+{str(int(dep_date.strftime('%d')))}" \
          f"+{dep_date.strftime('%b')}+{dep_date.strftime('%Y')}&date_to={ret_date.strftime('%a')}%2C+" \
          f"{str(int(ret_date.strftime('%d')))}+{ret_date.strftime('%b')}+{ret_date.strftime('%Y')}" \
          f"&adult_no=1&children_no=0&infant_no=0&currency={cur}&searchFlight="

    # Gets to url and gives HTML to BeautifulSoup parser.
    driver.get(url)
    sleep(2)
    source = driver.find_element(By.XPATH, "//section").get_attribute('outerHTML')
    soup = BeautifulSoup(source, 'html.parser')

    # Counts depart and return flights options.
    outbounds_indexes = len(soup.select('.fly5-depart>div.fly5-results>div:nth-of-type(n)'))
    inbounds_indexes = len(soup.select('.fly5-return>div.fly5-results>div:nth-of-type(n)'))

    # These loops combine all round trip flights.
    for out_index in range(outbounds_indexes):
        for in_index in range(inbounds_indexes):
            url_with_indexes.append([url, out_index, in_index])

    driver.quit()

    return url_with_indexes


def flight_details_scraper(url, out_idx, in_idx):
    """
    This function collects and returns required data from page.

    :param str url: url to flights page by required dates
    :param int out_idx: outbound flight card index
    :param int in_idx: inbound flight card index
    :return: list of scraped data from flight summary
    """

    # List to return.
    data = []

    # Gets to url by the given of function argument.
    driver.get(url)
    sleep(2)

    # Gets selected date from page and extracts year.
    depart_date = driver.find_element(By.XPATH, "//span[contains(text(),'Departing')]/..").text
    depart_year = re.search(r'\d{4}', depart_date)[0]
    return_date = driver.find_element(By.XPATH, "//span[contains(text(),'Returning')]/..").text
    return_year = re.search(r'\d{4}', return_date)[0]

    # Gets all outbounds cards and selects by index from function argument.
    all_outbounds = driver.find_elements(By.XPATH, "//div[@class='fly5-flights fly5-depart th']/"
                                                   "div[@class='fly5-results']/div")
    all_outbounds[out_idx].click()
    sleep(2)
    outbound_select_btn = all_outbounds[out_idx].find_element(By.XPATH, ".//button")
    outbound_select_btn.click()  # Chooses first/cheapest available SELECT button
    sleep(2)

    # Gets all inbounds cards and selects by index from function argument.
    all_inbounds = driver.find_elements(By.XPATH, "//div[@class='fly5-flights fly5-return th']/"
                                                  "div[@class='fly5-results']/div")
    all_inbounds[in_idx].click()
    sleep(2)
    inbound_select_btn = all_inbounds[in_idx].find_element(By.XPATH, ".//button")
    inbound_select_btn.click()  # Chooses first/cheapest available SELECT button
    sleep(2)

    # Clicks CONTINUE button.
    continue_btn = driver.find_element(By.XPATH, "//button[@id='continue-btn']")
    continue_btn.click()
    sleep(2)

    # REQUIRED DATA ARE BEING COLLECTED IN THIS PART.
    source = driver.find_element(By.XPATH, "//section").get_attribute('outerHTML')
    soup = BeautifulSoup(source, 'html.parser')

    # Outbound details (outbound departure and arrival airports codes, dates and times).
    out_from = soup.select('.fly5-fldet.fly5-fout>div>div.fly5-frshort')[0].text.replace(' ', '')
    out_to = soup.select('.fly5-fldet.fly5-fout>div>div.fly5-toshort')[0].text.replace(' ', '')
    out_dep_date = soup.select('.fly5-fldet.fly5-fout>div>div.fly5-timeout>span.fly5-fdate')[0].text
    out_dep_time = soup.select('.fly5-fldet.fly5-fout>div>div.fly5-timeout>span.fly5-ftime')[0].text
    out_arr_date = soup.select('.fly5-fldet.fly5-fout>div>div.fly5-timein>span.fly5-fdate')[0].text
    out_arr_time = soup.select('.fly5-fldet.fly5-fout>div>div.fly5-timein>span.fly5-ftime')[0].text

    # Inbound details (inbound departure and arrival airports codes, dates and times).
    in_from = soup.select('.fly5-fldet.fly5-fin>div>div.fly5-frshort')[0].text.replace(' ', '')
    in_to = soup.select('.fly5-fldet.fly5-fin>div>div.fly5-toshort')[0].text.replace(' ', '')
    in_dep_date = soup.select('.fly5-fldet.fly5-fin>div>div.fly5-timeout>span.fly5-fdate')[0].text
    in_dep_time = soup.select('.fly5-fldet.fly5-fin>div>div.fly5-timeout>span.fly5-ftime')[0].text
    in_arr_date = soup.select('.fly5-fldet.fly5-fin>div>div.fly5-timein>span.fly5-fdate')[0].text
    in_arr_time = soup.select('.fly5-fldet.fly5-fin>div>div.fly5-timein>span.fly5-ftime')[0].text

    # Gets total price.
    total_price = soup.select('.total>strong>span')[0].text.replace(' ', '')

    # Gets total taxes.
    all_taxes = soup.select('.fly5-bkdown>div:nth-of-type(2)>span')
    total_taxes = sum([float(x.text) for x in all_taxes])
    formatted_taxes = f"{total_taxes:,{'.2f'}}"  # Taxes are formatted as an example.

    def time_formatter(part_of_date, time, year):
        """
        This inner function formats and returns time as required.

        :param str part_of_date: Scraped date without year and time
        :param str time: Scraped time
        :param str year: Scraped year
        :return: Formatted full date as in example
        """
        full_date = f'{part_of_date} {time} {year}'  # Date is merged.
        date_datetime = datetime.strptime(full_date, "%a %d, %b %I:%M%p %Y").replace(
            tzinfo=timezone.utc)  # String converted to date format and changed time zone.
        date_str = date_datetime.strftime("%a %b %d %I:%M:%S GMT %Y")  # Date converted back to string and formatted.

        return date_str

    # Calls time_formatter function and add formatted dates to variables.
    outbound_departure_time = time_formatter(out_dep_date, out_dep_time, depart_year)
    outbound_arrival_time = time_formatter(out_arr_date, out_arr_time, depart_year)
    inbound_departure_time = time_formatter(in_dep_date, in_dep_time, return_year)
    inbound_arrival_time = time_formatter(in_arr_date, in_arr_time, return_year)

    # Appends collected data to data list outside this loop.
    data.append([out_from, out_to, outbound_departure_time, outbound_arrival_time, in_from, in_to,
                 inbound_departure_time, inbound_arrival_time, total_price, formatted_taxes])

    driver.quit()

    return data


def main():
    """
    This function is main and execute when the program is being run.

    Requirements:
    Collect required data from www.fly540.com for ALL round trip flight combinations from NBO (Nairobi) to MBA (Mombasa)
    departing 10 and 20 days from the current date and returning 7 days after the departure date.

    Required data:
    departure airport, arrival airport, departure time, arrival time, cheapest fare price, taxes.
    """

    # Defines variables according to requirements.
    depart_date_1 = date.today() + timedelta(days=10)
    return_date_1 = depart_date_1 + timedelta(days=7)
    depart_date_2 = date.today() + timedelta(days=20)
    return_date_2 = depart_date_2 + timedelta(days=7)

    departure_iata = 'NBO'
    arrival_iata = 'MBA'
    currency = 'USD'
    dates_list = [[depart_date_1, return_date_1], [depart_date_2, return_date_2]]

    # This part calls flights_scraper function twice with different arguments and executes it in parallel.
    flights_scraper_return = []

    try:
        # Sets max 'workers' number depending on the amount of arguments and CPU capability.
        workers = len(dates_list) if len(dates_list) < cpu_count() - 1 else cpu_count() - 1
        pool = Pool(workers)
        # This loop calls function twice and appends returned data to flights_scraper_return list.
        for dates in dates_list:
            flights_scraper_return.append(
                pool.apply_async(flights_scraper, args=(departure_iata, arrival_iata, currency, dates[0], dates[1],))
            )
        pool.close()
        pool.join()

        log('INFO', 'Flights page was successfully scraped.')
    except:
        log('Error', 'Failed to scrape flight page.')

    # This part calls flight_scraper_details function as many times as required,
    # depending on the number of arguments in the flights_scraper_return list and executes it in parallel.
    url_with_indexes = []

    for r in flights_scraper_return:  # Gets data from returned objects.
        url_with_indexes.extend([x for x in r.get()])

    data = []

    def get_result(result):
        data.extend(result)
        
    try:
        # Sets max 'workers' number depending on the amount of arguments and CPU capability.
        if len(url_with_indexes) < cpu_count():
            workers = len(url_with_indexes)
            pool = Pool(workers)
            for args in url_with_indexes:
                pool.apply_async(flight_details_scraper, args=(args[0], args[1], args[2],), callback=get_result)
            pool.close()
            pool.join()
            log('INFO', 'Flight summary page was successfully scraped in one round.')
        else:
            workers = cpu_count()
            pool = Pool(workers)
            for args in url_with_indexes[:workers]:
                pool.apply_async(flight_details_scraper, args=(args[0], args[1], args[2],), callback=get_result)
            pool.close()
            pool.join()

            new_workers = len(url_with_indexes[workers:])
            pool = Pool(new_workers)
            for args in url_with_indexes[workers:]:
                pool.apply_async(flight_details_scraper, args=(args[0], args[1], args[2],), callback=get_result)
            pool.close()
            pool.join()
            log('INFO', 'Flight summary page was successfully scraped in two rounds.')
    except:
        log('Error', 'Failed to scrape flight page.')

    # Saves collected data to result.csv.
    data_frame = pd.DataFrame(final_data, columns=['outbound_departure_airport',
                                                   'outbound_arrival_airport',
                                                   'outbound_departure_time',
                                                   'outbound_arrival_time',
                                                   'inbound_departure_airport',
                                                   'inbound_arrival_airport',
                                                   'inbound_departure_time',
                                                   'inbound_arrival_time',
                                                   'total_price',
                                                   'taxes'])
    
    sorted_df = data_frame.sort_values(['outbound_departure_time', 'inbound_departure_time'])
    file_exists = os.path.isfile('result.csv')  # Checks or such file exist. If not, set header=True.
    header = False
    if not file_exists:
        header = True

    try:
        # noinspection PyTypeChecker
        sorted_df.to_csv('result.csv', mode='a', sep=';', index=False, header=header)
        log('INFO', f'Data successfully wrote to result.csv')
    except:
        log('Error', f'Failed to write data to csv.')


if __name__ == "__main__":
    main()
