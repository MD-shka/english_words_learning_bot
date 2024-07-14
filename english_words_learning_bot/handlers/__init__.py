from aiogram import Dispatcher, Bot
from .start import register_start_handlers
from .stats import register_stats_handlers
from .learn import register_learn_handlers
from .settings import register_settings_handlers
from .general import register_general_handlers


def register_handlers(dp: Dispatcher, bot: Bot, config):
    register_start_handlers(dp, bot)
    register_stats_handlers(dp, bot)
    register_learn_handlers(dp, bot, config)
    register_settings_handlers(dp, bot)
    register_general_handlers(dp, bot)
