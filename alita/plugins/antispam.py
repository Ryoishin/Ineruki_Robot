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


from datetime import datetime
from io import BytesIO
from pyrogram.errors import MessageTooLong, PeerIdInvalid, UserIsBlocked
from pyrogram.types import Message
from traceback import format_exc

from ineruki import BOT_ID, LOGGER, MESSAGE_DUMP, SUPPORT_GROUP, SUPPORT_STAFF
from ineruki.bot_class import Ineruki
from ineruki.database.antispam_db import GBan
from ineruki.database.users_db import Users
from ineruki.tr_engine import tlang
from ineruki.utils.clean_file import remove_markdown_and_html
from ineruki.utils.custom_filters import command
from ineruki.utils.extract_user import extract_user
from ineruki.utils.parser import mention_html

# Initialize
db = GBan()


@Ineruki.on_message(command(["gban", "globalban"], sudo_cmd=True))
async def gban(c: Ineruki, m: Message):
    if len(m.text.split()) == 1:
        await m.reply_text(tlang(m, "antispam.gban.how_to"))
        return

    if len(m.text.split()) == 2 and not m.reply_to_message:
        await m.reply_text(tlang(m, "antispam.gban.enter_reason"))
        return

    user_id, user_first_name, _ = await extract_user(c, m)

    if m.reply_to_message:
        gban_reason = m.text.split(None, 1)[1]
    else:
        gban_reason = m.text.split(None, 2)[2]

    if user_id in SUPPORT_STAFF:
        await m.reply_text(tlang(m, "antispam.part_of_support"))
        return

    if user_id == BOT_ID:
        await m.reply_text(tlang(m, "antispam.gban.not_self"))
        return

    if db.check_gban(user_id):
        db.update_gban_reason(user_id, gban_reason)
        await m.reply_text(
            (tlang(m, "antispam.gban.updated_reason")).format(
                gban_reason=gban_reason,
            ),
        )
        return

    db.add_gban(user_id, gban_reason, m.from_user.id)
    await m.reply_text(
        (tlang(m, "antispam.gban.added_to_watch")).format(
            first_name=user_first_name,
        ),
    )
    LOGGER.info(f"{m.from_user.id} gbanned {user_id} from {m.chat.id}")
    log_msg = (tlang(m, "antispam.gban.log_msg")).format(
        chat_id=m.chat.id,
        ban_admin=(await mention_html(m.from_user.first_name, m.from_user.id)),
        gbanned_user=(await mention_html(user_first_name, user_id)),
        gban_user_id=user_id,
        time=(datetime.utcnow().strftime("%H:%M - %d-%m-%Y")),
    )
    await c.send_message(MESSAGE_DUMP, log_msg)
    try:
        # Send message to user telling that he's gbanned
        await c.send_message(
            user_id,
            (tlang(m, "antispam.gban.user_added_to_watch")).format(
                gban_reason=gban_reason,
                SUPPORT_GROUP=SUPPORT_GROUP,
            ),
        )
    except UserIsBlocked:
        LOGGER.error("Could not send PM Message, user blocked bot")
    except PeerIdInvalid:
        LOGGER.error(
            "Haven't seen this user anywhere, mind forwarding one of their messages to me?",
        )
    except Exception as ef:  # TO DO: Improve Error Detection
        LOGGER.error(ef)
        LOGGER.error(format_exc())
    return


@Ineruki.on_message(
    command(["ungban", "unglobalban", "globalunban"], sudo_cmd=True),
)
async def ungban(c: Ineruki, m: Message):
    if len(m.text.split()) == 1:
        await m.reply_text(tlang(m, "antispam.pass_user_id"))
        return

    user_id, user_first_name, _ = await extract_user(c, m)

    if user_id in SUPPORT_STAFF:
        await m.reply_text(tlang(m, "antispam.part_of_support"))
        return

    if user_id == BOT_ID:
        await m.reply_text(tlang(m, "antispam.ungban.not_self"))
        return

    if db.check_gban(user_id):
        db.remove_gban(user_id)
        await m.reply_text(
            (tlang(m, "antispam.ungban.removed_from_list")).format(
                first_name=user_first_name,
            ),
        )
        LOGGER.info(f"{m.from_user.id} ungbanned {user_id} from {m.chat.id}")
        log_msg = (tlang(m, "amtispam.ungban.log_msg")).format(
            chat_id=m.chat.id,
            ungban_admin=(await mention_html(m.from_user.first_name, m.from_user.id)),
            ungbaned_user=(await mention_html(user_first_name, user_id)),
            ungbanned_user_id=user_id,
            time=(datetime.utcnow().strftime("%H:%M - %d-%m-%Y")),
        )
        await c.send_message(MESSAGE_DUMP, log_msg)
        try:
            # Send message to user telling that he's ungbanned
            await c.send_message(
                user_id,
                (tlang(m, "antispam.ungban.user_removed_from_list")),
            )
        except Exception as ef:  # TODO: Improve Error Detection
            LOGGER.error(ef)
            LOGGER.error(format_exc())
        return

    await m.reply_text(tlang(m, "antispam.ungban.non_gbanned"))
    return


@Ineruki.on_message(
    command(["numgbans", "countgbans", "gbancount", "gbanscount"], sudo_cmd=True),
)
async def gban_count(_, m: Message):
    await m.reply_text(
        (tlang(m, "antispam.num_gbans")).format(count=(db.count_gbans())),
    )
    LOGGER.info(f"{m.from_user.id} counting gbans in {m.chat.id}")
    return


@Ineruki.on_message(
    command(["gbanlist", "globalbanlist"], sudo_cmd=True),
)
async def gban_list(_, m: Message):
    banned_users = db.load_from_db()

    if not banned_users:
        await m.reply_text(tlang(m, "antispam.none_gbanned"))
        return

    banfile = tlang(m, "antispam.here_gbanned_start")
    for user in banned_users:
        banfile += f"[x] <b>{Users.get_user_info(user['_id'])['name']}</b> - <code>{user['_id']}</code>\n"
        if user["reason"]:
            banfile += f"<b>Reason:</b> {user['reason']}\n"

    try:
        await m.reply_text(banfile)
    except MessageTooLong:
        with BytesIO(str.encode(await remove_markdown_and_html(banfile))) as f:
            f.name = "gbanlist.txt"
            await m.reply_document(
                document=f,
                caption=tlang(m, "antispam.here_gbanned_start"),
            )

    LOGGER.info(f"{m.from_user.id} exported gbanlist in {m.chat.id}")

    return
