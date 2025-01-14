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


from pyrogram import filters
from pyrogram.errors import (
    ChatAdminInviteRequired,
    ChatAdminRequired,
    RightForbidden,
    RPCError,
    UserAdminInvalid,
)
from pyrogram.types import Message
from traceback import format_exc

from ineruki import LOGGER, SUPPORT_GROUP, SUPPORT_STAFF
from ineruki.bot_class import Ineruki
from ineruki.database.approve_db import Approve
from ineruki.database.reporting_db import Reporting
from ineruki.tr_engine import tlang
from ineruki.utils.caching import ADMIN_CACHE, TEMP_ADMIN_CACHE_BLOCK, admin_cache_reload
from ineruki.utils.custom_filters import DEV_LEVEL, admin_filter, command, promote_filter
from ineruki.utils.extract_user import extract_user
from ineruki.utils.parser import mention_html


@Ineruki.on_message(command("adminlist") & filters.group)
async def adminlist_show(_, m: Message):
    global ADMIN_CACHE
    try:
        try:
            admin_list = ADMIN_CACHE[m.chat.id]
            note = tlang(m, "admin.adminlist.note_cached")
        except KeyError:
            admin_list = await admin_cache_reload(m, "adminlist")
            note = tlang(m, "admin.adminlist.note_updated")

        adminstr = (tlang(m, "admin.adminlist.adminstr")).format(
            chat_title=m.chat.title,
        ) + "\n\n"

        bot_admins = [i for i in admin_list if (i[1].lower()).endswith("bot")]
        user_admins = [i for i in admin_list if not (i[1].lower()).endswith("bot")]

        # format is like: (user_id, username/name,anonyamous or not)
        mention_users = [
            (
                admin[1]
                if admin[1].startswith("@")
                else (await mention_html(admin[1], admin[0]))
            )
            for admin in user_admins
            if not admin[2]  # if non-anonyamous admin
        ]
        mention_users.sort(key=lambda x: x[1])

        mention_bots = [
            (
                admin[1]
                if admin[1].startswith("@")
                else (await mention_html(admin[1], admin[0]))
            )
            for admin in bot_admins
        ]
        mention_bots.sort(key=lambda x: x[1])

        adminstr += "<b>User Admins:</b>\n"
        adminstr += "\n".join(f"- {i}" for i in mention_users)
        adminstr += "\n\n<b>Bots:</b>\n"
        adminstr += "\n".join(f"- {i}" for i in mention_bots)

        await m.reply_text(adminstr + "\n\n" + note)
        LOGGER.info(f"Adminlist cmd use in {m.chat.id} by {m.from_user.id}")

    except Exception as ef:
        if str(ef) == str(m.chat.id):
            await m.reply_text(tlang(m, "admin.adminlist.use_admin_cache"))
        else:
            ef = str(ef) + f"{admin_list}\n"
            await m.reply_text(
                (tlang(m, "general.some_error")).format(
                    SUPPORT_GROUP=SUPPORT_GROUP,
                    ef=ef,
                ),
            )
        LOGGER.error(ef)
        LOGGER.error(format_exc())

    return


@Ineruki.on_message(
    command("admincache") & admin_filter,
)
async def reload_admins(_, m: Message):
    global TEMP_ADMIN_CACHE_BLOCK
    if m.chat.type != "supergroup":
        return
    if (
            (m.chat.id in set(TEMP_ADMIN_CACHE_BLOCK.keys()))
            and (m.from_user.id not in SUPPORT_STAFF)
            and TEMP_ADMIN_CACHE_BLOCK[m.chat.id] == "manualblock"
    ):
        await m.reply_text("Can only reload admin cache once per 10 mins!")
        return

    try:
        await admin_cache_reload(m, "admincache")
        TEMP_ADMIN_CACHE_BLOCK[m.chat.id] = "manualblock"
        await m.reply_text(tlang(m, "admin.adminlist.reloaded_admins"))
        LOGGER.info(f"Admincache cmd use in {m.chat.id} by {m.from_user.id}")
    except RPCError as ef:
        await m.reply_text(
            (tlang(m, "general.some_error")).format(
                SUPPORT_GROUP=SUPPORT_GROUP,
                ef=ef,
            ),
        )
        LOGGER.error(ef)
        LOGGER.error(format_exc())
    return


@Ineruki.on_message(filters.regex(r"^(?i)@admin(s)?") & filters.group)
async def tag_admins(_, m: Message):
    db = Reporting(m.chat.id)
    if not db.get_settings():
        return

    try:
        admin_list = ADMIN_CACHE[m.chat.id]
    except KeyError:
        admin_list = await admin_cache_reload(m, "adminlist")

    user_admins = [i for i in admin_list if not (i[1].lower()).endswith("bot")]
    mention_users = [(await mention_html("\u2063", admin[0])) for admin in user_admins]
    mention_users.sort(key=lambda x: x[1])
    mention_str = "".join(mention_users)
    await m.reply_text(
        (
            f"{(await mention_html(m.from_user.first_name, m.from_user.id))}"
            f" reported the message to admins!{mention_str}"
        ),
    )


@Ineruki.on_message(
    command("promote") & promote_filter,
)
async def promote_usr(c: Ineruki, m: Message):
    from ineruki import BOT_ID

    global ADMIN_CACHE

    if len(m.text.split()) == 1 and not m.reply_to_message:
        await m.reply_text(tlang(m, "admin.promote.no_target"))
        return

    user_id, user_first_name, user_name = await extract_user(c, m)
    
    bot = await c.get_chat_member(m.chat.id, BOT_ID)

    if user_id == BOT_ID:
        await m.reply_text("Huh, how can I even promote myself?")
        return

    if not bot.can_promote_members:
        return await m.reply_text("I don't have enough permissions") # This should be here 
    # If user is alreay admin
    try:
        admin_list = {i[0] for i in ADMIN_CACHE[m.chat.id]}
    except KeyError:
        admin_list = {
            i[0] for i in (await admin_cache_reload(m, "promote_cache_update"))
        }

    if user_id in admin_list:
        await m.reply_text(
            "This user is already an admin, how am I supposed to re-promote them?",
        )
        return

    try:
        await m.chat.promote_member(
            user_id=user_id,
            can_change_info=bot.can_change_info,
            can_invite_users=bot.can_invite_users,
            can_delete_messages=bot.can_delete_messages,
            can_restrict_members=bot.can_restrict_members,
            can_pin_messages=bot.can_pin_messages,
        #    can_promote_members=bot.can_promote_members,
            can_manage_chat=bot.can_manage_chat,
            can_manage_voice_chats=bot.can_manage_voice_chats,
        )

        title = "Admin"  # Deafult title
        if len(m.text.split()) == 3 and not m.reply_to_message:
            title = m.text.split()[2]
        elif len(m.text.split()) == 2 and m.reply_to_message:
            title = m.text.split()[1]
        if len(title) > 16:
            title = title[0:16]  # trim title to 16 characters

        await c.set_administrator_title(m.chat.id, user_id, title)

        LOGGER.info(
            f"{m.from_user.id} promoted {user_id} in {m.chat.id} with title '{title}'",
        )

        await m.reply_text(
            (tlang(m, "admin.promote.promoted_user")).format(
                promoter=(await mention_html(m.from_user.first_name, m.from_user.id)),
                promoted=(await mention_html(user_first_name, user_id)),
                chat_title=m.chat.title + f"\nTitle set to {title}"
                if title != "Admin"
                else "",
            ),
        )

        # If user is approved, disapprove them as they willbe promoted and get even more rights
        if Approve(m.chat.id).check_approve(user_id):
            Approve(m.chat.id).remove_approve(user_id)

        # ----- Add admin to temp cache -----
        try:
            inp1 = user_name or user_first_name
            admins_group = ADMIN_CACHE[m.chat.id]
            admins_group.append((user_id, inp1))
            ADMIN_CACHE[m.chat.id] = admins_group
        except KeyError:
            await admin_cache_reload(m, "promote_key_error")

    except ChatAdminRequired:
        await m.reply_text(tlang(m, "admin.not_admin"))
    except RightForbidden:
        await m.reply_text(tlang(m, "admin.promote.bot_no_right"))
    except UserAdminInvalid:
        await m.reply_text(tlang(m, "admin.user_admin_invalid"))
    except RPCError as ef:
        await m.reply_text(
            (tlang(m, "general.some_error")).format(
                SUPPORT_GROUP=SUPPORT_GROUP,
                ef=ef,
            ),
        )
        LOGGER.error(ef)
        LOGGER.error(format_exc())

    return


@Ineruki.on_message(
    command("demote") & promote_filter,
)
async def demote_usr(c: Ineruki, m: Message):
    from ineruki import BOT_ID

    global ADMIN_CACHE

    if len(m.text.split()) == 1 and not m.reply_to_message:
        await m.reply_text(tlang(m, "admin.demote.no_target"))
        return

    user_id, user_first_name, _ = await extract_user(c, m)

    if user_id == BOT_ID:
        await m.reply_text("Get an admin to demote me!")
        return

    # If user not alreay admin
    try:
        admin_list = {i[0] for i in ADMIN_CACHE[m.chat.id]}
    except KeyError:
        admin_list = {
            i[0] for i in (await admin_cache_reload(m, "demote_cache_update"))
        }

    if user_id not in admin_list:
        await m.reply_text(
            "This user is not an admin, how am I supposed to re-demote them?",
        )
        return

    try:
        await m.chat.promote_member(
            user_id=user_id,
            can_change_info=False,
            can_invite_users=False,
            can_delete_messages=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_promote_members=False,
            can_manage_chat=False,
            can_manage_voice_chats=False,
        )
        LOGGER.info(f"{m.from_user.id} demoted {user_id} in {m.chat.id}")

        # ----- Remove admin from cache -----
        try:
            admin_list = ADMIN_CACHE[m.chat.id]
            user = next(user for user in admin_list if user[0] == user_id)
            admin_list.remove(user)
            ADMIN_CACHE[m.chat.id] = admin_list
        except (KeyError, StopIteration):
            await admin_cache_reload(m, "demote_key_stopiter_error")

        await m.reply_text(
            (tlang(m, "admin.demote.demoted_user")).format(
                demoter=(await mention_html(m.from_user.first_name, m.from_user.id)),
                demoted=(await mention_html(user_first_name, user_id)),
                chat_title=m.chat.title,
            ),
        )

    except ChatAdminRequired:
        await m.reply_text(tlang(m, "admin.not_admin"))
    except RightForbidden:
        await m.reply_text(tlang(m, "admin.demote.bot_no_right"))
    except UserAdminInvalid:
        await m.reply_text(tlang(m, "admin.user_admin_invalid"))
    except RPCError as ef:
        await m.reply_text(
            (tlang(m, "general.some_error")).format(
                SUPPORT_GROUP=SUPPORT_GROUP,
                ef=ef,
            ),
        )
        LOGGER.error(ef)
        LOGGER.error(format_exc())

    return


@Ineruki.on_message(
    command("invitelink"),
)
async def get_invitelink(c: Ineruki, m: Message):
    # Bypass the bot devs, sudos and owner
    if m.from_user.id not in DEV_LEVEL:
        user = await m.chat.get_member(m.from_user.id)

        if not user.can_invite_users and user.status != "creator":
            await m.reply_text(tlang(m, "admin.no_user_invite_perm"))
            return False

    try:
        link = await c.export_chat_invite_link(m.chat.id)
        await m.reply_text(
            (tlang(m, "admin.invitelink")).format(
                chat_name=m.chat.id,
                link=link,
            ),
            disable_web_page_preview=True,
        )
        LOGGER.info(f"{m.from_user.id} exported invite link in {m.chat.id}")
    except ChatAdminRequired:
        await m.reply_text(tlang(m, "admin.not_admin"))
    except ChatAdminInviteRequired:
        await m.reply_text(tlang(m, "admin.no_invite_perm"))
    except RightForbidden:
        await m.reply_text(tlang(m, "admin.no_user_invite_perm"))
    except RPCError as ef:
        await m.reply_text(
            (tlang(m, "general.some_error")).format(
                SUPPORT_GROUP=SUPPORT_GROUP,
                ef=ef,
            ),
        )
        LOGGER.error(ef)
        LOGGER.error(format_exc())

    return


__PLUGIN__ = "admin"
