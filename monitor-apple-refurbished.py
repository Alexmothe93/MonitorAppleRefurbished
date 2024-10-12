import requests

import json
import re
import time
from dataclasses import dataclass

from config import *

@dataclass
class Product:
    title: str
    partNumber: str
    price: str
    stillAvailable: bool = False

def sendDiscordMessage(message):
    print(message)
    data = {
        "content" : message,
        "username" : discordUsername,
        "avatar_url" : discordAvatarURL
    }
    try:
        requests.post(discordWebhookURL, json = data)
    except Exception as err:
        print(f"An error occured trying to send Discord message : {err=}, {type(err)=}")

def wait():
    time.sleep(timeCheckInterval)

def withoutHTML(text):
    clean = re.compile('<.*>')
    return re.sub(clean, '', text)

alertedProducts: [Product] = []

while True:
    try:
        r = requests.get(URL)
        
        if r.status_code != 200:
            sendDiscordMessage("Error "+str(r.status_code)+" getting the web page.")
            wait()
            continue
        
        refurbGridBootstraps = re.findall(r'REFURB_GRID_BOOTSTRAP = (\{.+\});', r.text)

        if refurbGridBootstraps:
            refurbishedProducts = json.loads(refurbGridBootstraps[0])["tiles"]
        else:
            sendDiscordMessage("Error: REFURB_GRID_BOOTSTRAP content not found.")
            wait()
            continue

        if refurbishedProducts:
            for product in alertedProducts:
                product.stillAvailable = False

            for product in refurbishedProducts:
                if float(product["price"]["currentPrice"]["raw_amount"]) <= maxTargetPrice:
                    targetedProduct = Product(product["title"], product["partNumber"], product["price"]["currentPrice"]["amount"])
                    targetedProduct = Product(product["title"], product["partNumber"], withoutHTML(product["price"]["currentPrice"]["amount"]))
                    if targetedProduct in alertedProducts:
                        alertedProducts[alertedProducts.index(targetedProduct)].stillAvailable = True
                    else:
                        sendDiscordMessage(targetedProduct.price+" : "+targetedProduct.title+"\nhttps://www.apple.com"+product["productDetailsUrl"])
                        targetedProduct.stillAvailable = True
                        alertedProducts.append(targetedProduct)

            for product in alertedProducts:
                if not product.stillAvailable:
                    sendDiscordMessage(product.title+" à "+product.price+" n'est plus disponible.")
                    alertedProducts.remove(product)

    except Exception as err:
        sendDiscordMessage(f"Unexpected {err=}, {type(err)=}")
        
    wait()