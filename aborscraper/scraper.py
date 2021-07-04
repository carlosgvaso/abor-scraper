## Scraper module to scrape the ABOR favorite listings page
#

import argparse
from bs4 import BeautifulSoup as bs
import csv
import json
import logging
import os.path
import requests
from types import SimpleNamespace

# Globals
args = None
conf = None

# Settings
conf_file_default = '../conf/conf.json'

# Export results to a CSV file
def export_results_csv(csv_file, results):
    """ Export results to a CSV file
    """
    fieldnames = ['Address', 'Status', 'Price', 'Bedrooms', 'Bathrooms', 'HouseAreaSqft', 'PropertyAreaAc', 'YearBuilt', 'MLS']
    with open(csv_file, 'w+', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_NONNUMERIC)

        writer.writeheader()
        for row in results:
            writer.writerow(row)

# Extract results from raw soup
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

        logging.info('Favorite property %d:', fave_cnt)
        logging.info('  MLS number: %d', listing_mls)
        logging.info('  Address: %s', listing_addr)
        logging.info('  Market status: %s', listing_status)
        logging.info('  Price: %d', listing_price)
        logging.info('  Number of bedrooms: %d', listing_beds)
        logging.info('  Number of bathrooms: %d', listing_baths)
        logging.info('  House area (sqft): %d', listing_house_area)
        logging.info('  Property area (ac): %f', listing_property_area)
        logging.info('  Year built: %d', listing_year_built)

        faves.append(
            {
                'Address': listing_addr,
                'Status': listing_status,
                'Price': listing_price,
                'Bedrooms': listing_beds,
                'Bathrooms': listing_baths,
                'HouseAreaSqft': listing_house_area,
                'PropertyAreaAc': listing_property_area,
                'YearBuilt': listing_year_built,
                'MLS': listing_mls
            })

    return faves

# Get raw web page content
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

# Parse command-line arguments
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

# Parse configuration file
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

    return conf

# Set up logger
def set_logger(conf):
    """Set up logger
    """
    logging.basicConfig(
            filename=conf.log_file,
            #encoding='utf-8',
            level=conf.log_level,
            format='%(asctime)s:%(levelname)s:%(module)s:%(funcName)s: %(message)s')

# Main
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
    bs_raw = get_page(conf.url)

    # Extract results
    logging.info('Extracting results...')
    results = extract_results(bs_raw)

    # Export results to CSV
    export_results_csv(conf.csv_file, results)

    logging.info('Done')

# Entry point
if __name__ == '__main__':
    main()