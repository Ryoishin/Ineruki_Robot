# Copyright (C) 2020 - 2021 Divkix. All rights reserved. Source code available under the AGPL.
#
# This file is part of Ineruki_Robot.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from html import escape
from pyrogram.types import Message
from secrets import choice

from ineruki.bot_class import Ineruki
from ineruki.tr_engine import tlang
from ineruki.utils import fun_strings
from ineruki.utils.custom_filters import command
from ineruki.utils.extract_user import extract_user


@Ineruki.on_message(command("shout"))
async def fun_shout(_, m: Message):
    if len(m.text.split()) == 1:
        await m.reply_text(
            (tlang(m, "general.check_help")),
            quote=True,
        )
        return
    text = " ".join(m.text.split(None, 1)[1])
    result = [" ".join(list(text))]
    for pos, symbol in enumerate(text[1:]):
        result.append(symbol + " " + "  " * pos + symbol)
    result = list("\n".join(result))
    result[0] = text[0]
    result = "".join(result)
    msg = "```\n" + result + "```"
    await m.reply_text(msg, parse_mode="MARKDOWN")
    return


@Ineruki.on_message(command("runs"))
async def fun_run(_, m: Message):
    await m.reply_text(choice(fun_strings.RUN_STRINGS))
    return


@Ineruki.on_message(command("slap"))
async def fun_slap(c: Ineruki, m: Message):
    me = await c.get_me()

    reply_text = m.reply_to_message.reply_text if m.reply_to_message else m.reply_text

    curr_user = escape(m.from_user.first_name)
    user_id, _, _ = await extract_user(c, m)

    if user_id == me.id:
        temp = choice(fun_strings.SLAP_ALITA_TEMPLATES)
    else:
        temp = choice(fun_strings.SLAP_TEMPLATES)

    if user_id:
        slapped_user = await c.get_users(user_id)
        user1 = curr_user
        user2 = escape(slapped_user.first_name)

    else:
        user1 = me.first_name
        user2 = curr_user

    item = choice(fun_strings.ITEMS)
    hit = choice(fun_strings.HIT)
    throw = choice(fun_strings.THROW)

    reply = temp.format(user1=user1, user2=user2, item=item, hits=hit, throws=throw)

    await reply_text(reply)
    return


@Ineruki.on_message(command("roll"))
async def fun_roll(_, m: Message):
    reply_text = m.reply_to_message.reply_text if m.reply_to_message else m.reply_text
    await reply_text(choice(range(1, 7)))
    return


@Ineruki.on_message(command("toss"))
async def fun_toss(_, m: Message):
    reply_text = m.reply_to_message.reply_text if m.reply_to_message else m.reply_text
    await reply_text(choice(fun_strings.TOSS))
    return


@Ineruki.on_message(command("shrug"))
async def fun_shrug(_, m: Message):
    reply_text = m.reply_to_message.reply_text if m.reply_to_message else m.reply_text
    await reply_text(r"¯\_(ツ)_/¯")
    return


@Ineruki.on_message(command("bluetext"))
async def fun_bluetext(_, m: Message):
    reply_text = m.reply_to_message.reply_text if m.reply_to_message else m.reply_text
    await reply_text(
        "/BLUE /TEXT\n/MUST /CLICK\n/I /AM /A /STUPID /ANIMAL /THAT /IS /ATTRACTED /TO /COLORS",
    )
    return


@Ineruki.on_message(command("decide"))
async def fun_decide(_, m: Message):
    reply_text = m.reply_to_message.reply_text if m.reply_to_message else m.reply_text
    await reply_text(choice(fun_strings.DECIDE))
    return


@Ineruki.on_message(command("react"))
async def fun_table(_, m: Message):
    reply_text = m.reply_to_message.reply_text if m.reply_to_message else m.reply_text
    await reply_text(choice(fun_strings.REACTIONS))
    return


__PLUGIN__ = "fun"
