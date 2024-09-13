import configparser
from escpos import printer
from urllib.request import urlretrieve
import requests
import json
from PIL import Image
import time
from future.backports.datetime import datetime

def create_config():
    # Create a new configuration file
    config = configparser.ConfigParser()

    # Add a 'Printer' section with key-value pairs for printer settings
    config['Printer'] = {
        'idVendor': '0x0416',
        'idProduct': '0x5011',
        'in_ep': '0x81',
        'out_ep': '0x03',
        'profile': 'TM-P80'
    }

    # Write the configuration to 'config.ini'
    with open('config.ini', 'w') as configfile:
        config.write(configfile)

def read_config():
    # Create a ConfigParser object to read the configuration file
    config = configparser.ConfigParser()

    # Read the 'config.ini' file
    config.read('config.ini')

    # Extract values from the configuration file and store them in a dictionary
    config_values = {
        'idVendor': config.get('Printer', 'idVendor'),
        'idProduct': config.get('Printer', 'idProduct'),
        'in_ep': config.get('Printer', 'in_ep'),
        'out_ep': config.get('Printer', 'out_ep'),
        'profile': config.get('Printer', 'profile')
    }

    return config_values

def fetch_info(upc):
    # Fetch information from the UPC Item DB API
    url = f'https://api.upcitemdb.com/prod/trial/lookup?upc={upc}'
    response = requests.get(url)

    try:
        # Raise an exception if the request failed
        response.raise_for_status()
        upc_data = json.loads(response.text)
        rate_limit_remaining = response.headers['X-RateLimit-Remaining']
        rate_limit_reset = response.headers['X-RateLimit-Reset']
    except:
        # Handle exceptions and rate limit errors
        rate_limit_remaining = response.headers.get('X-RateLimit-Remaining', 'N/A')
        rate_limit_reset = response.headers.get('X-RateLimit-Reset', 'N/A')

        if rate_limit_remaining == "0":
            # If API rate limit is exceeded
            renew_time = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(int(rate_limit_reset)))
            reply = f"You've exceeded your API rate!\nIt will refresh at {renew_time}"
            return reply, None, rate_limit_remaining, rate_limit_reset
        else:
            # If the URL is invalid
            return "Invalid URL!\n", None, rate_limit_remaining, rate_limit_reset

    # Parse the response data
    data = upc_data['items']

    # Retrieve the title, description, and image URL from the API response
    info = "Title: \n"
    try:
        info += data[0]['title']
    except:
        info += "No title!"
    info += "\nDescription: \n"
    try:
        info += data[0]['description']
    except:
        info += "No description!"
    info += "\n"
    try:
        imgurl = data[0]['images'][0]
    except:
        imgurl = "No image!"

    # Retrieve the merchandise link from the API response
    try:
        merch_link = data[0]['offers'][0]['link']
    except:
        merch_link = "No merch link!"

    return info, imgurl, merch_link, rate_limit_remaining, rate_limit_reset

def print_expiry(renew):
    # Print the rate limit expiry information
    p.text("\n\n")
    p.set(align="center")
    renew_time = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(int(renew)))
    p.text(f"You have {remaining} request(s)\n")
    p.set(align="center")
    p.text(f"Until {renew_time}")
    p.text("\n")

def fetch_image(url):
    # Fetch and resize the image from the URL
    try:
        path, headers = urlretrieve(url)
        image = Image.open(path)
        return image.resize((576, 576))
    except:
        return "No image!"

def print_header():
    # Print the header with the current date and time
    p.image('./assets/logo.png', center=True)
    p.ln(3)
    now = datetime.now().strftime('%m/%d/%Y %H:%M:%S %Z')
    p.text(f'Printed at: {now}\n')
    p.ln(1)

# Main program
try:
    # Try to read the configuration file
    config = read_config()
except:
    # If reading fails, create a new configuration file and prompt the user to configure
    create_config()
    print("Please use the config.ini file to configure your printer.")
    exit(1)

# Initialize the USB printer with the configuration
p = printer.Usb(
    int(config['idVendor'], 16),
    int(config['idProduct'], 16),
    in_ep=int(config['in_ep'], 16),
    out_ep=int(config['out_ep'], 16),
    profile=str(config['profile'])
)

# Main loop for fetching and printing UPC information
while True:
    info, image_url, merch_link, remaining, renew = fetch_info(input("Enter the UPC: "))
    p.hw("INIT")
    print_header()
    p.text(info)

    try:
        # Print the image if available
        p.image(fetch_image(image_url))
    except:
        p.text('No image!')

    p.hw('INIT')

    # Print the merchandise link QR code if available
    if merch_link != 'No merch link!':
        p.set(align='center', double_width=True, double_height=True)
        p.text('\n\nBuy Here\n\n')
        p.qr(str(merch_link), native=True, size=4)
        p.text('\n')
    else:
        p.ln(1)
        p.text(merch_link)
        p.ln(1)

    # Print the rate limit expiry information
    print_expiry(renew)
    p.cut()
