import configparser
from escpos import printer
from urllib.request import urlretrieve
import requests
import json
from PIL import Image
import time

def create_config():
    config = configparser.ConfigParser()

    # Add sections and key-value pairs
    config['Printer'] = {'idVendor': '0x0416', 'idProduct': '0x5011',
                         'in_ep': '0x81', 'out_ep': '0x03', 'profile': 'TM-P80'}

    # Write the configuration to a file
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


def read_config():
    # Create a ConfigParser object
    config = configparser.ConfigParser()

    # Read the configuration file
    config.read('config.ini')

    # Access values from the configuration file
    idVendor = config.get('Printer', 'idVendor')
    idProduct = config.get('Printer', 'idProduct')
    in_ep = config.get('Printer', 'in_ep')
    out_ep = config.get('Printer', 'out_ep')
    profile = config.get('Printer', 'profile')

    # Return a dictionary with the retrieved values
    config_values = {
        'idVendor': idVendor,
        'idProduct': idProduct,
        'in_ep': in_ep,
        'out_ep': out_ep,
        'profile': profile
    }

    return config_values

def fecthinfo (upc):
    url = 'https://api.upcitemdb.com/prod/trial/lookup?upc=%s' % upc
    response = requests.get(url)
    try:
        response.raise_for_status()
        upcData = json.loads(response.text)
        tomuch = response.headers['X-RateLimit-Remaining']
        renew = response.headers['X-RateLimit-Reset']
    except:
        tomuch = response.headers['X-RateLimit-Remaining']
        renew = response.headers['X-RateLimit-Reset']
        if tomuch == "0":
            renewtime = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime(int(response.headers['X-RateLimit-Reset'])))
            reply = ("You've exceeded your API rate!\n"
                     "It will refresh at %s") % renewtime
            imgurl = None
            return reply, imgurl, tomuch, renew
        else:
            imgurl = None
            reply = "Invalid URL!\n"
            return reply, imgurl, tomuch, renew
    data = upcData['items']
    info = "Title: \n"
    try:
        info += data[0]['title']
    except:
        info += "No title!"
    info += "\n"
    info += "Description: \n"
    try:
        info += data[0]['description']
    except:
        info += "No description!"
    info += "\n"
    try:
        imgurl = data[0]['images']
        imgurl = (imgurl[0])
    except:
        imgurl = "No image!"
    return info, imgurl, tomuch, renew

def printexp(renew):
    p.text("\n\n")
    p.set(align="center")
    renew = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime(int(renew)))
    p.text("You have %s request(s)\n" % remaining)
    p.set(align="center")
    p.text("Until %s" % renew)
    p.text("\n")

def fetchIMG(url):
        try:
            path, headers = urlretrieve(url)
            image = Image.open(path)
            return image.resize((576, 576))
        except:
            return "No image!"

try:
    config = read_config()
except:
    create_config()
    print("Please use the config.ini file to configure your printer.")
    exit(1)

p = printer.Usb(int(config['idVendor'], 16), int(config['idProduct'], 16), in_ep=int(config['in_ep'], 16),
                out_ep=int(config['out_ep'], 16), profile=str(config['profile']))

while True:
    info, imageurl, remaining, renew = fecthinfo(input("Put in the damn fuckin UPC! "))
    print
    p.hw("INIT")
    p.text(info)
    try:
        p.image(fetchIMG(imageurl))
    except:
        if imageurl != None:
            p.text(fetchIMG(imageurl))
    printexp(renew)
    p.cut()
