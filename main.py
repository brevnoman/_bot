import asyncio
import os

from aiogram.contrib.fsm_storage.memory import MemoryStorage
import logging
from aiogram.dispatcher.filters import Text
from motor import motor_asyncio
from aiogram import Bot, Dispatcher, executor, types
import aiohttp

from keyboards import start, second, third_step, get_next

logging.basicConfig(level=logging.INFO)
storage = MemoryStorage()
bot = Bot(token=os.environ["TOKEN"])
dp = Dispatcher(bot, storage=storage)
cluster = motor_asyncio.AsyncIOMotorClient(
    os.environ["DATABASE_URL"]
)
collection = cluster.TestDB.TestCollection
base_api_url = "https://coinpay.org.ua/"


@dp.callback_query_handler(Text(startswith="start_"))
@dp.message_handler(commands=["start"])
async def start_menu(message: (types.Message, types.CallbackQuery)):
    user = await collection.find_one(
        {
            "_id": message.from_user.id
        }
    )
    if not user:
        collection.insert_one(
            {
                "_id": message.from_user.id,
            }
        )
    markup = await start()
    if isinstance(message, types.Message):
        await message.answer(text="Choose main currency", reply_markup=markup)
    else:
        await message.message.edit_text(text="Choose main currency")
        await message.message.edit_reply_markup(reply_markup=markup)


@dp.callback_query_handler(Text(startswith="income_currency_"))
async def second_currency(call: types.CallbackQuery):
    markup = await second(call)
    await collection.update_one({"_id": call.from_user.id}, {"$set": {"is_active": False}})
    await call.message.edit_text(text="Choose second currency")
    await call.message.edit_reply_markup(reply_markup=markup)


@dp.callback_query_handler(Text(startswith="currency_pair_"))
async def choose_interval(call: types.CallbackQuery):
    currency_pair = call["data"].replace("currency_pair_", "")
    markup = await third_step(collection, call, currency_pair)
    user = await collection.find_one({"_id": call.from_user.id})
    if not user.get("interval"):
        await call.message.edit_text(text="Input interval in minutes for update using\n/interval [interval]\nCommand")
        await call.message.edit_reply_markup(reply_markup=markup)
    else:
        call["data"] = call["data"].replace("currency_pair_", "turn_on_")
        await start_updating(call)
    await collection.update_one({'_id': call.from_user.id}, {"$set": {"currency_pair": currency_pair}})


@dp.callback_query_handler(Text(startswith="turn_on_"))
async def start_updating(call: types.CallbackQuery):
    url = base_api_url + "api/v1/exchange_rate"
    pair_with_interval = call["data"].replace("turn_on_", "")
    first, second = pair_with_interval.split("_")
    await collection.update_one({'_id': call.from_user.id}, {
        "$set": {
            "currency_pair": f"{first}_{second}",
            "is_active": True,
        }
    })
    needed_currency = None
    async with aiohttp.ClientSession() as session:
        async with session.get(url=url) as resp:
            currencies = await resp.json()
            for currency in currencies["rates"]:
                if currency["pair"] == f"{first}_{second}":
                    needed_currency = currency
    markup = await get_next(first, second)
    if needed_currency is None:
        await call.message.edit_text(text="Sorry but there is no suck currencies pair")
    else:
        await call.message.edit_text(text=f"You need {needed_currency['base_currency_price']} {second} to buy 1 {first}")
    await call.message.edit_reply_markup(reply_markup=markup)
    user = await collection.find_one({"_id": call.from_user.id})
    await update_information(call, interval=user["interval"])


async def update_information(call: types.CallbackQuery, interval):
    await asyncio.sleep(interval)
    user = await collection.find_one({"_id": call.from_user.id})
    if user.get("is_active"):
        call["data"] = "turn_on_" + user["currency_pair"]
        await start_updating(call)


@dp.message_handler(commands=["interval"])
async def set_interval(message: types.Message):
    interval = message.text.replace("/interval", "").strip()
    if interval.isdecimal():
        await collection.update_one({'_id': message.from_user.id}, {'$set': {'interval': int(interval)}})
        await message.answer(text=f"your interval set for {interval} minutes")
    else:
        await message.answer(text="your interval should be number")


async def on_startup(_):
    users = collection.find({}).sort("_id")
    async for user in users:
        if user.get("interval") and user.get("currency_pair") and user.get("is_active"):
            print(user)


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
