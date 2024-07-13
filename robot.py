import asyncio
import os

import botpy
from botpy import logging
from botpy.ext.cog_yaml import read
from botpy.message import GroupMessage, Message
from getExihibition import GetInfo, GetExtraInfo

test_config = read(os.path.join(os.path.dirname(__file__), "config.yaml"))

_log = logging.get_logger()

class MyClient(botpy.Client):
    async def on_ready(self):
        _log.info(f"robot 「{self.robot.name}」 on_ready!")

    async def on_group_at_message_create(self, message: GroupMessage):
        msg = message.content.split()
        if msg[0] == "/会展":
            if len(msg) < 2:
                messageResult = await message._api.post_group_message(
                group_openid=message.group_openid,
                msg_type=0, 
                msg_id=message.id,
                content=f"使用方式 @我 /会展 会展城市")
            else:
                messageResult = await message._api.post_group_message(
                    group_openid=message.group_openid,
                    msg_type=0, 
                    msg_id=message.id,
                    content=f"{GetInfo(msg[1])}")
            _log.info(messageResult)

        elif msg[0] == "/会展详情": # doing
            if len(msg) < 2:
                messageResult = await message._api.post_group_message(
                group_openid=message.group_openid,
                msg_type=0, 
                msg_id=message.id,
                content=f"使用方式 @我 /会展详情 会展名或id")
            else:
                messageResult = await message._api.post_group_message(
                    group_openid=message.group_openid,
                    msg_type=0, 
                    msg_id=message.id,
                    content=f"{GetExtraInfo(msg()[1])}")
            _log.info(messageResult)

if __name__ == "__main__":
    # 通过预设置的类型，设置需要监听的事件通道
    # intents = botpy.Intents.none()
    # intents.public_messages=True

    # 通过kwargs，设置需要监听的事件通道
    intents = botpy.Intents(public_messages=True)
    client = MyClient(intents=intents)
    client.run(appid=test_config["appid"], secret=test_config["secret"])