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

def convertedCapacityOf(capacity):
    if "gb" in capacity:
        return int(capacity.removesuffix("gb"))
    elif "tb" in capacity:
        return int(capacity.removesuffix("tb")) * 1024
    else:
        sendDiscordMessage("Error trying to convert "+capacity+" into number.")

def meetsTheCriteria(product):
    if "raw_amount" in product["price"]["currentPrice"] and "dimensions" in product["filters"]:
        rawAmount = float(product["price"]["currentPrice"]["raw_amount"])
        filtersDimensions = product["filters"]["dimensions"]
    else:
        sendDiscordMessage("Failed to retrieve specifications.")
        return False
    
    if  rawAmount > maxTargetPrice:
        return False
    
    if "dimensionCapacity" in filtersDimensions and convertedCapacityOf(filtersDimensions["dimensionCapacity"]) < minStorageGB:
        return False

    if "tsMemorySize" in filtersDimensions and convertedCapacityOf(filtersDimensions["tsMemorySize"]) < minRAM:
        return False

    if "dimensionRelYear" in filtersDimensions and int(filtersDimensions["dimensionRelYear"]) < minYear:
        return False

    if "refurbClearModel" in filtersDimensions and filtersDimensions["refurbClearModel"] not in wantedProducts:
        return False

    return True

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
        
        if r.status_code == 500:
            sendDiscordMessage("Error 500 getting the web page: "+URL)
            wait()
            continue
        elif r.status_code == 503:
            print("Error 503 getting the web page, Apple Store is unavailable.")
            wait()
            continue
        elif r.status_code != 200:
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
                if meetsTheCriteria(product):
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