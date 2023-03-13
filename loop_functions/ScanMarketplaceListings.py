import os
from dbqueries.MarketplaceFunctions import marketplace as marketFunctions
from datetime import datetime
from dateutil.parser import parse

async def checkListings():
    all_listings = marketFunctions.query.getAllMarketplaceItems()

    active_listings = []
    for listing in all_listings:
        if listing['ended'] == False:
            active_listings.append(listing)

    for listing in active_listings:
        if listing['endDate'] != '0':
            end_date = parse(listing['endDate'])
            time_diff = end_date - datetime.now()
            if time_diff.days <= -1:
                await marketFunctions.listing.updateListing(listing, ended=True)