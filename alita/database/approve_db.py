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


from threading import RLock
from time import time

from ineruki import LOGGER
from ineruki.database import MongoDB

INSERTION_LOCK = RLock()


class Approve(MongoDB):
    """Class for managing Approves in Chats in Bot."""

    # Database name to connect to to preform operations
    db_name = "approve"

    def __init__(self, chat_id: int) -> None:
        super().__init__(self.db_name)
        self.chat_id = chat_id
        self.chat_info = self.__ensure_in_db()

    def check_approve(self, user_id: int):
        with INSERTION_LOCK:
            return bool(user_id in self.chat_info["users"])

    def add_approve(self, user_id: int, user_name: str):
        with INSERTION_LOCK:
            self.chat_info["users"].append((user_id, user_name))
            if not self.check_approve(user_id):
                return self.update(
                    {"_id": self.chat_id},
                    {"users": self.chat_info["users"]},
                )
            return True

    def remove_approve(self, user_id: int):
        with INSERTION_LOCK:
            if self.check_approve(user_id):
                user_full = next(
                    user for user in self.chat_info["users"] if user[0] == user_id
                )
                self.chat_info["users"].pop(user_full)
                return self.update(
                    {"_id": self.chat_id},
                    {"users": self.chat_info["users"]},
                )
            return True

    def unapprove_all(self):
        with INSERTION_LOCK:
            return self.delete_one(
                {"_id": self.chat_id},
            )

    def list_approved(self):
        with INSERTION_LOCK:
            return self.chat_info["users"]

    def count_approved(self):
        with INSERTION_LOCK:
            return len(self.chat_info["users"])

    def load_from_db(self):
        return self.find_all()

    def __ensure_in_db(self):
        chat_data = self.find_one({"_id": self.chat_id})
        if not chat_data:
            new_data = {"_id": self.chat_id, "users": ()}
            self.insert_one(new_data)
            LOGGER.info(f"Initialized Approve Document for chat {self.chat_id}")
            return new_data
        return chat_data

    # Migrate if chat id changes!
    def migrate_chat(self, new_chat_id: int):
        old_chat_db = self.find_one({"_id": self.chat_id})
        new_data = old_chat_db.update({"_id": new_chat_id})
        self.insert_one(new_data)
        self.delete_one({"_id": self.chat_id})

    @staticmethod
    def count_all_approved():
        with INSERTION_LOCK:
            collection = MongoDB(Approve.db_name)
            all_data = collection.find_all()
            return sum(len(i["users"]) for i in all_data if len(i["users"]) >= 1)

    @staticmethod
    def count_approved_chats():
        with INSERTION_LOCK:
            collection = MongoDB(Approve.db_name)
            all_data = collection.find_all()
            return sum(len(i["users"]) >= 1 for i in all_data)

    @staticmethod
    def repair_db(collection):
        all_data = collection.find_all()
        keys = {"users": []}
        for data in all_data:
            for key, val in keys.items():
                try:
                    _ = data[key]
                except KeyError:
                    LOGGER.warning(
                        f"Repairing Approve Database - setting '{key}:{val}' for {data['_id']}",
                    )
                    collection.update({"_id": data["_id"]}, {key: val})


def __pre_req_approve():
    start = time()
    LOGGER.info("Starting Approve Database Repair...")
    collection = MongoDB(Approve.db_name)
    Approve.repair_db(collection)
    LOGGER.info(f"Done in {round((time() - start), 3)}s!")
