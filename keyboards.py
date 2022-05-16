import aiohttp
from aiogram import types


base_api_url = "https://coinpay.org.ua/"


async def start():
    markup = types.InlineKeyboardMarkup(row_width=2)
    url = base_api_url + "/api/v1/currency"
    async with aiohttp.ClientSession() as session:
        async with session.get(url=url) as resp:
            currencies = await resp.json()
    for currency in currencies["currencies"]:
        markup.add(
            types.InlineKeyboardButton(
                text=currency, callback_data=f"income_currency_{currency}")
        )
    return markup


async def second(call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    url = base_api_url + "/api/v1/currency"
    async with aiohttp.ClientSession() as session:
        async with session.get(url=url) as resp:
            currencies = await resp.json()
    first_currency = call["data"].replace("income_currency_", "")
    for currency in currencies["currencies"]:
        if currency != first_currency:
            markup.add(
                types.InlineKeyboardButton(
                    text=currency, callback_data=f"currency_pair_{first_currency}_{currency}")
            )
    markup.add(
        types.InlineKeyboardButton(
            text="back", callback_data="start_"
        )
    )
    return markup


async def third_step(collection, call, currency_pair):
    markup = types.InlineKeyboardMarkup(row_width=2)
    first_currency = currency_pair.split("_")[0]
    await collection.update_one({"_id": call.from_user.id}, {"$set": {"currency_pair": currency_pair}})
    markup.add(
        types.InlineKeyboardButton(
            text="Turn on", callback_data=f"currency_pair_{currency_pair}"
        ),
        types.InlineKeyboardButton(
            text="Back", callback_data=f"income_currency_{first_currency}"
        )
    )
    return markup


async def get_next(first, second):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(
            text="Update", callback_data=f"turn_on_{first}_{second}"
        ),
        types.InlineKeyboardButton(
            text="Back", callback_data=f"income_currency_{first}"
        )
    )
    return markup