## Scraper module to scrape the ABOR favorite listings page
#
# @author   Carlos Garcia-Vaso <carlosgvaso@gmail.com>

import argparse
from bs4 import BeautifulSoup as bs
import csv
import gspread
import json
import logging
from oauth2client.service_account import ServiceAccountCredentials
import os.path
import requests
from types import SimpleNamespace

## Globals
args = None
conf = None

## Settings
conf_file_default = '../conf/conf.json'

## Export results to a CSV file
def export_results_csv(results, csv_file):
    """ Export results to a CSV file
    """
    logging.debug('fieldnames = %s', conf.csv_schema)
    with open(csv_file, 'w+', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=conf.csv_schema, quoting=csv.QUOTE_NONNUMERIC)

        writer.writeheader()
        for row in results:
            writer.writerow(row)

## Export results to Google Drive
def export_results_gdrive(results):
    """ Export results to Google Drive
    """
    # Define the scope
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']

    # Add credentials to the account
    creds = ServiceAccountCredentials.from_json_keyfile_name(conf.key_file, scope)

    # Authorize the clientsheet 
    client = gspread.authorize(creds)

    # Get the instance of the Spreadsheet
    sheet = client.open(conf.sheet_title)

    # Get the first sheet of the Spreadsheet
    sheet_instance = sheet.get_worksheet(0)

    # Prepare results to be inserted
    values = format_results_gsheets(results)

    # Insert results
    sheet_instance.insert_rows(values, row=2, value_input_option='RAW')

## Extract results from raw soup
def extract_results(raw_bs):
    """ Extract results from raw soup"""
    faves = list()

    # Find DIV encompassing all favorite listings
    fave_div = raw_bs.find(id='_ctl0_m_divAsyncPagedDisplays')
    if logging.root.level == logging.DEBUG:
        fave_div_pretty = fave_div.prettify()
        with open('../log/fave_div.html', 'w+') as fo:
            fo.write(fave_div_pretty)

    # Get all results in the div
    entries = fave_div.find_all('div', class_='col-lg-7 col-md-6 col-sm-12')

    fave_cnt = 0
    for entry in entries:
        fave_cnt += 1

        if logging.root.level == logging.DEBUG:
            entry_pretty = entry.prettify()
            with open('../log/entry{}.html'.format(fave_cnt), 'w+') as fo:
                fo.write(entry_pretty)

        # Process entry
        listing_data = entry.find_all('span', class_='d-text')
        logging.debug('listing_data = %s', listing_data)

        # Get listing price
        listing_price = int(listing_data[0].text.replace('$', '').replace(',', ''))

        # Get listing MLS number
        listing_mls = int(listing_data[2].text)

        # Get listing number of bedrooms
        listing_beds = int(listing_data[3].text)

        # Get listing number of bathrooms
        listing_baths = int(listing_data[4].text)

        # Get listing house area in sqft
        listing_house_area = int(listing_data[5].text.replace(',', ''))

        # Get listing year built
        listing_year_built = int(listing_data[6].text)

        # Get listing property area in acres
        listing_property_area = float(listing_data[7].text)

        # Get listing market status
        status_span = entry.find('div', 'col-xs-9 d-fontSize--small col-sm-8 col-md-8 col-lg-8').find('span', class_='formula J_formula').find('span')
        logging.debug('status_span = %s', status_span)
        if status_span:
            listing_status = status_span.text
        else:
            listing_status = str('N/A')

        # Get listing address
        listing_addr1 = entry.find('div', class_='col-sm-12 d-fontSize--largest d-text d-color--brandDark').find('span', class_='formula J_formula').find('a').text
        logging.debug('listing_addr1 = %s', listing_addr1)
        listing_addr2 = entry.find('div', class_='col-sm-12 d-fontSize--small d-textSoft d-paddingBottom--8').find('span', class_='formula J_formula').text
        logging.debug('listing_addr2 = %s', listing_addr2)
        listing_addr = listing_addr1 + str(', ') + listing_addr2

        # Get listing URL
        listing_url = conf.url_abor

        logging.info('Favorite property %d:', fave_cnt)
        logging.info('  Address: %s', listing_addr)
        logging.info('  Price: %d', listing_price)
        logging.info('  Bedrooms: %d', listing_beds)
        logging.info('  Bathrooms: %d', listing_baths)
        logging.info('  House Area (Sqft): %d', listing_house_area)
        logging.info('  Property Area (Acres): %f', listing_property_area)
        logging.info('  Year Built: %d', listing_year_built)
        logging.info('  Market Status: %s', listing_status)
        logging.info('  MLS: %d', listing_mls)
        logging.info('  Link: %s', listing_url)

        faves.append(
            {
                'Address': listing_addr,
                'Price': listing_price,
                'Bedrooms': listing_beds,
                'Bathrooms': listing_baths,
                'House Area (Sqft)': listing_house_area,
                'Property Area (Acres)': listing_property_area,
                'Year Built': listing_year_built,
                'Market Status': listing_status,
                'MLS': listing_mls,
                'Link': listing_url
            })

    return faves

## Format results from CSV dictionary format to Google Sheets API format
#
# Google Sheets format is the format used by
# gspread.models.Worksheet.insert_rows() function for the values parameter:
# https://docs.gspread.org/en/latest/api.html#gspread.models.Worksheet.insert_rows
def format_results_gsheets(results):
    """Format results from CSV dictionary format to Google Sheets API format

    Google Sheets format is the format used by
    gspread.models.Worksheet.insert_rows() function for the values parameter:
    https://docs.gspread.org/en/latest/api.html#gspread.models.Worksheet.insert_rows
    """
    results_fmt = list()

    # Add each result to the list
    for result in results:
        row = list()

        # Add each field to the list in order, or empty field
        for field in conf.sheet_schema:
            # I f we have a value for the field, add it
            if field in result:
                row.append(result.get(field))
            # If the field is Status, set it to 'new'
            elif field == conf.sheet_schema[0]:
                row.append(str('new'))
            # Else, set it to empty
            else:
                row.append(str())

        results_fmt.append(row)

    # Add empty row to separate from previous data
    row = list()
    for field in conf.sheet_schema:
        row.append(str())
    results_fmt.append(row)

    logging.debug('results_fmt = %s', results_fmt)
    return results_fmt

## Get raw web page content
def get_page(url):
    """ Get raw web page content"""
    # Get the page code
    page = requests.get(url)

    # Get soup
    raw_bs = bs(page.content, 'html.parser') # Make BeautifulSoup object

    # Save the page code if debugging
    if logging.root.level == logging.DEBUG:
        page_pretty = raw_bs.prettify() # Prettify the html

        with open('../log/webpage.html', 'w+') as fo:
            fo.write(page_pretty)
    
    return raw_bs

## Parse command-line arguments
def parse_args():
    """ Parse command-line arguments
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
            '-c', '--conf-file',
            default=conf_file_default,
            help='Configuration file path')
    parser.add_argument('-l', '--log-level', help='Logger verbosity level')
    args = parser.parse_args()

    # Check arguments
    if args.log_level is not None:
        try:
            args.log_level = logging._checkLevel(args.log_level.upper())
        except:
            print('ERROR:scrapper:parse_args: Log level no recognized: %s', args.log_level)
            exit(1)
    args.conf_file = os.path.realpath(args.conf_file)

    return args

## Parse configuration file
def parse_config(conf_file):
    """Parse config file
    """
    conf = None
    with open(conf_file, 'r') as cfile:
        conf = json.load(cfile, object_hook=lambda d: SimpleNamespace(**d))

    # Check arguments
    if args.log_level is None:
        try:
            conf.log_level = logging._checkLevel(conf.log_level.upper())
        except:
            print('ERROR:scrapper:parse_config: Log level no recognized: %s', conf.log_level)
            exit(1)
    else:
        conf.log_level = args.log_level
    
    conf.csv_file = os.path.realpath(conf.csv_file)
    conf.log_file = os.path.realpath(conf.log_file)
    conf.key_file = os.path.realpath(conf.key_file)

    return conf

## Set up logger
def set_logger(conf):
    """Set up logger
    """
    logging.basicConfig(
            filename=conf.log_file,
            #encoding='utf-8',
            level=conf.log_level,
            format='%(asctime)s:%(levelname)s:%(module)s:%(funcName)s: %(message)s')

## Main
def main():
    """ Entry point
    """
    global args
    global conf

    # Parse command-line arguments
    args = parse_args()

    # Parse config
    conf = parse_config(args.conf_file)

    # Set up logger
    set_logger(conf)

    logging.debug('args = %s', args)
    logging.debug('conf = %s', conf)

    # Get raw web page soup
    logging.info('Getting raw page content...')
    bs_raw = get_page(conf.url_abor)

    # Extract results
    logging.info('Extracting results...')
    results = extract_results(bs_raw)

    # Export results to CSV
    export_results_csv(results, conf.csv_file)

    # Export results to Google Drive
    export_results_gdrive(results)

    logging.info('Done')

## Entry point
if __name__ == '__main__':
    main()