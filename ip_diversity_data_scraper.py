'''
This script fetches IP diversity data from multiple servers and stores the results in a JSON file. 
Also this categorizes URLs based on their status, such as found, not found, timeout, and other errors. 
'''

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import json
import logging
import time
import pytz


'''
applying loggers 
'''
logging.basicConfig(level=logging.INFO, filename='ip_diversity_data_scraper.log', filemode='a',
                    format=' %(lineno)d - %(asctime)s - %(name)s - %(levelname)s - %(message)s ')
logger = logging.getLogger()


'''
Converting date into standard date format:-dd-mm-yy
'''
def convert_date_format(date_str):
    formats = ["%y-%m-%d", "%m/%d/%y"]
    for fmt in formats:
        try:
            date_obj = datetime.strptime(date_str, fmt)
            return date_obj.strftime("%d-%m-%y")
        except ValueError as e:
            logger.error("getting error in date '%s' in converting into '%s' and the error is %s", date_str, fmt, e)
            continue
    return date_str


'''
fetching ip diversity data from multiple servers and store the results in the JSON file.
'''
if __name__ == '__main__':    
    df = pd.read_excel("an_node_config.xlsx", engine='openpyxl')
    ips = df['node_ip'].tolist()
    server_names = df['server_name'].tolist()

    # categorizationing for different types of urls:
    final_list = []
    not_found_links_list = []
    timeout_links = []
    other_links = []
    tableData_notFoundlinks = []
    down_ips = []
    for ip, server_name in zip(ips, server_names):
        individual_server_dict = {}
        url = "http://" + ip.strip() + "/ipdiversity.html"  # Forming the URL from IP address
        logger.info("Attempting to fetch data from URL:- %s", url)
        retries = 3  # For timeout url 
        for attempt in range(retries):
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, "html.parser")
                individual_server_dict[server_name.upper()] = {"url": url}
                ip_diversity_dict_with_dates = {}
                h3_tag = soup.find('h3', string=lambda text: text and text.lower() == "last 10 days ip diversity")
                if h3_tag:
                    table = h3_tag.find_next_sibling('table')
                    if table:
                        headers = table.find_all("th")
                        date_index = -1
                        ip_diversity_index = -1
                        for idx, header in enumerate(headers):
                            header_text = header.get_text(strip=True).lower()
                            if "date" in header_text:
                                date_index = idx
                            elif "ip diversity %" in header_text:
                                ip_diversity_index = idx
                        if date_index != -1 and ip_diversity_index != -1:
                            rows = table.find_all("tr")
                            for row in rows[1:]:
                                cells = row.find_all('th')
                                if len(cells) > max(date_index, ip_diversity_index):
                                    date_key = cells[date_index].get_text(strip=True)
                                    formatted_date = convert_date_format(date_key)
                                    value = cells[ip_diversity_index].get_text(strip=True) + "%"
                                    ip_diversity_dict_with_dates[formatted_date] = value
                if ip_diversity_dict_with_dates:
                    individual_server_dict[server_name.upper()]["ipdiversity"] = ip_diversity_dict_with_dates
                    final_list.append(individual_server_dict)  # append into final list
                else:

                    # if table not found
                    logger.warning("table data not found for %s", ip)
                    tableData_notFoundlinks.append(ip)
                    down_ips.append({
                        "server_name": server_name,
                        "status": "Table data not found"
                    })
                break
            except requests.exceptions.Timeout:
                logger.error("timeout url %s, attempt %d", ip, attempt + 1)
                if attempt == retries - 1:
                    timeout_links.append(ip)
                    down_ips.append({
                        "server_name": server_name,
                        "status": "Timeout"
                    })
            except requests.exceptions.RequestException as err:
                logger.error("Error fetching URL %s: %s", url, err)
                if attempt == retries - 1:
                    logger.error("Not found IP: %s after %d attempts", ip, retries)
                    not_found_links_list.append(ip)
                    down_ips.append({
                        "server_name": server_name,
                        "status": "Not found"
                    })
            except Exception as e:
                logger.error("Other error for URL %s: %s", url, e)
                if attempt == retries - 1:
                    logger.error("Other error for IP: %s after %d attempts", ip, retries)
                    other_links.append(ip)
                    down_ips.append({
                        "server_name": server_name,
                        "status": "Other error"
                    })

    # collecting all dates for sorting purpose 
    dates = set()
    for server_data in final_list:
        for server, details in server_data.items():
            dates.update(details['ipdiversity'].keys())
    sorted_dates = sorted(dates, reverse=True)

    # Getting the current time in IST
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    formatted_time = now.strftime("%d-%m-%Y %H:%M:%S")
    result_data = {
        "final_list": final_list,
        "down_ips": down_ips,
        "last_run_time": formatted_time
    }

    # dump into json file
    with open('ip_diversity_details.json', 'w') as file:
        json.dump(result_data, file)
    logger.info("Completed")
