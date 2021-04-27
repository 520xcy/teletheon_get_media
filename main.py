from telethon import TelegramClient, sync, errors, events, utils
from telethon.tl.types import PeerChannel, MessageMediaWebPage, PeerChat,InputPeerUser
from telethon.tl.functions.messages import ForwardMessagesRequest
from telethon.tl.functions.messages import SendMessageRequest
from telethon.tl.functions.account import UpdateStatusRequest
from telethon.tl.functions.channels import GetChannelsRequest
from telethon.tl.functions.users import GetUsersRequest

import random
import time
import socks
import os
import time
import re
import json
from log import get_logger

class tg_watchon_class:

    def __init__(self):

        self.conf = self.get_conf()
        self.api_id = self.conf['api']
        self.api_hash = self.conf['api_hash']

        self.wltlist = []

        if self.conf['proxyhost'] and self.conf['proxyport']:
            self.client = TelegramClient('some_name', self.api_id, self.api_hash,
                                     proxy=(socks.SOCKS5, self.conf['proxyhost'], self.conf['proxyport'])).start()
        else:
            self.client = TelegramClient('some_name', self.api_id, self.api_hash).start()

        for wlt in self.conf['whiltlist']:
            entity = self.client.get_entity(wlt)
            self.wltlist.append(entity.id)

        @self.client.on(events.NewMessage)
        async def handler(event):
            # print("handler init success")
            # print('sender: ' + str(event.input_sender) + 'to: ' + str(event.message.to_id))
            entity = await self.client.get_entity(event.message.to_id)
            sender = await event.get_sender()
            # logger.error(f'entity.id: {entity.id}')
            if sender.id == self.conf['admin_id']:
                raw_text = event.raw_text.strip()
                if raw_text.strip().startswith('/history'):
                    for xx in self.conf['history']:
                        await event.reply(f'Start Download {xx[0]}')
                        # await self.client.send_message(InputPeerUser(
                        #     sender.id, sender.access_hash), f'Start Download {xx[0]}')
                        try:
                            await self.history_download(xx[0], xx[1], xx[2])
                        except:
                            await event.reply(f'Download Fail {xx[0]}')
                            pass
                        else:
                            await event.reply(f'Download Complete {xx[0]}')
                    return

                        # await self.client.send_message(InputPeerUser(
                        #     sender.id, sender.access_hash), f'Download Complete {xx[0]}')
                elif raw_text.startswith('/download'):
                    xx = raw_text.split(' ')
                    print(xx)
                    if len(xx)<4:
                        await event.reply(f'命令格式错误 /download 频道链接 开始id 数量')
                    else:
                        await event.reply(f'Start Download {xx[1]}')
                        try:
                            await self.history_download(xx[1], int(xx[2]), int(xx[3]))
                        except:
                            await event.reply(f'Download Fail {xx[1]}')
                            pass
                        else:
                            await event.reply(f'Download Complete {xx[1]}')
                    return

                elif raw_text.startswith('/help'):
                    await event.reply(f'下载指定频道历史媒体文件: /download 频道链接 开始id 数量\n下载配置中频道历史文件: /history\n重载config.json文件(api设置重载无效): /reload')
                    return
                elif raw_text.startswith('/reload'):
                    self.conf = self.get_conf()
                    await event.reply(f'重载config.json')
                    return


            logger.info(
                f'sender: {str(event.input_sender)} to: {str(event.message.to_id)}')

            if entity.id in self.wltlist:
                if event.media is not None:
                    try:
                        await self.media_download(entity.id, event)
                    except Exception as e:
                        if self.conf['error_notice']:
                            await self.client.forward_messages(self.conf['error_notice'], event.message)
                        pass
                    else:
                        if self.conf['forward_channel']:
                            await self.client.forward_messages(self.conf['forward_channel'], event.message)
                        pass

            # if not event.raw_text == '':
            #     msg = 'sender: ' + str(event.input_sender) + ' #### to: ' + str(
            #         event.message.to_id) + ' #### Message: ' + event.raw_text
            #     logger.info(f'{msg}')\

    async def history_download(self, chat_id, offset_id, limit):
        entity = await self.client.get_entity(chat_id)
        async for event in self.client.iter_messages(entity, offset_id=offset_id, reverse=True, limit=limit):
            if event.media is not None:
                try:
                    await self.media_download(entity.id, event)
                except:
                    if self.conf['error_notice']:
                        await self.client.forward_messages(self.conf['error_notice'], event)
                    pass
                else:
                    if self.conf['forward_channel']:
                        await self.client.forward_messages(self.conf['forward_channel'], event)
                    pass

    async def media_download(self, entity_id, event):
        file_name = self.get_filename(event)
        if file_name == False:
            return

        file_name = os.path.join(data_storage_path, str(
            entity_id), file_name)

        if os.path.isfile(file_name):
            logger.critical(f'文件已存在:{file_name}')
            return

        logger.critical(f'Start Download File: {file_name}')
        try:
            await self.client.download_media(event.media, file_name)
        except:
            os.remove(file_name)
            logger.error(f'{entity_id}:{file_name}')
            raise
        else:
            logger.critical(f'Finish Download File: {file_name}')


    def get_filename(self, event):
        file_name = ''
        if event.document:
            try:
                if type(event.media) == MessageMediaWebPage:
                    return
                if event.media.document.mime_type == "image/webp":
                    file_name = f'{event.media.document.id}.webp'
                if event.media.document.mime_type == "application/x-tgsticker":
                    file_name = f'{event.media.document.id}.tgs'
                for i in event.document.attributes:
                    try:
                        file_name = i.file_name
                    except:
                        continue
            except:
                print(event.media)

        if event.photo:
            file_name = f'{event.photo.id}.jpg'
        elif file_name == '':
            file_name = self.get_random_file_name()
            _extension = str(event.media.document.mime_type)
            _extension = _extension.split('/')[-1]
            file_name = f'{file_name}.{_extension}'

        if not event.raw_text == '':
            file_name = str(event.raw_text).replace(
                '\n', ' ') + ' ' + file_name
        if any(_name in file_name for _name in self.conf['filename_block']):
            return False
        _file_name, _extension = os.path.splitext(file_name)
        file_name = f'{event.id} - {self.format_filename(_file_name)}{_extension}'
        return file_name

    def get_conf(self):
        with open(os.path.join(os.getcwd(), 'conf.json'), 'r', encoding='UTF-8') as r:
            return json.loads(r.read())

    def get_client(self):
        return self.client

    def start(self):
        print('(Press Ctrl+C to stop this)')
        self.client.run_until_disconnected()

    def format_filename(self, f):
        f = re.sub(
            u"([^\u4e00-\u9fa5\u0030-\u0039\u0041-\u005a\u0061-\u007a])", "", f)
        try:
            while len(f.encode('utf-8')) > 210:
                f = f[0:-1]
        except:
            pass
        return f
    
    def get_random_file_name(self):
        H = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        salt = ''
        for i in range(22):
            salt += random.choice(H)
        t_dir = time.strftime("%Y-%m-%d", time.localtime())
        return salt

if __name__ == '__main__':
    
    data_storage_path = os.path.join(os.getcwd(), 'data_online')
    logger = get_logger(__name__, 'WARNING')

    t = tg_watchon_class()
    t.start()