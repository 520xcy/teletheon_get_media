from telethon import TelegramClient, sync, errors, events, utils
from telethon.tl.types import PeerChannel, MessageMediaWebPage, PeerChat
from telethon.tl.functions.messages import ForwardMessagesRequest
from telethon.tl.functions.messages import SendMessageRequest
from telethon.tl.functions.account import UpdateStatusRequest
from telethon.tl.functions.channels import GetChannelsRequest
from telethon.tl.functions.users import GetUsersRequest

import random
import time
import socks
import os
import logging
import time
import re
from multiprocessing import Process, cpu_count
from conf import config
from log import get_logger

from logging.handlers import RotatingFileHandler

def format_filename(f):
    f = re.sub(
        u"([^\u4e00-\u9fa5\u0030-\u0039\u0041-\u005a\u0061-\u007a])", "", f)
    try:
        while len(f.encode('utf-8')) > 210:
            f = f[0:-1]
    except:
        pass
    return f


def checkFileExist(fileURI):
    if os.path.isfile(fileURI):
        logger.critical(f'文件已存在:{fileURI}')
        return True
    return False


def get_local_time():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def format_filename(f):
    f = re.sub(
        u"([^\u4e00-\u9fa5\u0030-\u0039\u0041-\u005a\u0061-\u007a])", "", f)
    try:
        while len(f.encode('utf-8')) > 210:
            f = f[0:-1]
    except:
        pass
    return f

# 下载 history 不是实时监听 实时监听在 `tg_watchon_class`
def get_filename(event):
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
        file_name = config().get_random_file_name()
        _extension = str(event.media.document.mime_type)
        _extension = _extension.split('/')[-1]
        file_name = f'{file_name}.{_extension}'

    if not event.raw_text == '':
        file_name = str(event.raw_text).replace(
            '\n', ' ') + ' ' + file_name

    _file_name, _extension = os.path.splitext(file_name)
    file_name = f'{event.id} - {format_filename(_file_name)}{_extension}'
    return file_name

def history_download(chat_id, offset_id, limit, client):
    entity = client.get_entity(chat_id)
    for event in client.iter_messages(entity, offset_id=offset_id, reverse=True, limit=limit):
        if event.media is not None:
            file_name = get_filename(event)
            file_name = os.path.join(data_storage_path, str(
                entity.id), file_name)
            if checkFileExist(file_name):
                continue
            msg = 'File: ' + file_name
            logger.critical(f'{msg}')
            try:
                client.download_media(event.media, file_name)
            except (ValueError,Exception) as e:
                msg = f'{event.id}:{file_name} - {e}'
                logger.error(f'{msg}')
                pass
            except KeyboardInterrupt:
                os.remove(file_name)
                exit()
            except:
                msg = f'{event.id}:{file_name}'
                logger.error(f'{msg}')
                os.remove(file_name)
                pass


class tg_watchon_class:

    def __init__(self):
        self.data_storage_path = config().getpath()
        self.api_id = config().get_api()
        self.api_hash = config().get_api_hash()
        self.whiltlist = []

        self.client = TelegramClient('some_name', self.api_id, self.api_hash,
                                     proxy=(socks.SOCKS5, '192.168.12.230', 1083)).start()

        wailtlist = config().get_whiltlist()

        for wlt in wailtlist['channels']:
            self.whiltlist.append(PeerChannel(wlt))

        for wlt in wailtlist['chats']:
            self.whiltlist.append(PeerChat(wlt))

        @self.client.on(events.NewMessage)
        async def handler(event):
            # print("handler init success")
            # print('sender: ' + str(event.input_sender) + 'to: ' + str(event.message.to_id))
            # entity = await self.client.get_entity(event.message.to_id)
            # logger.error(f'entity.id: {entity.id}')

            logger.error(f'sender: {str(event.input_sender)} to: {str(event.message.to_id)}')

            if event.message.to_id in self.whiltlist:
                # if event.raw_text == '':
                if event.media is not None:
                    
                    file_name = get_filename(event)

                    t_dir = time.strftime("%Y-%m-%d", time.localtime())
                    file_name = os.path.join(self.data_storage_path, str(
                        event.message.to_id), t_dir, file_name)
                    msg = 'File: ' + file_name
                    logger.critical(f'{msg}')
                    try:
                        await self.client.download_media(event.media, file_name)
                    except errors.TimeoutError as e:
                        msg = f'{event.id}:{file_name} - errors.TimeoutError {e}'
                        logger.error(f'{msg}')
                        os.remove(file_name)
                        pass
                    except (ValueError,Exception) as e:
                        msg = f'{event.id}:{file_name} - {e}'
                        logger.error(f'{msg}')
                        os.remove(file_name)
                        pass
                    except:
                        os.remove(file_name)
                        pass
            # if not event.raw_text == '':
            #     msg = 'sender: ' + str(event.input_sender) + ' #### to: ' + str(
            #         event.message.to_id) + ' #### Message: ' + event.raw_text
            #     logger.info(f'{msg}')

    def get_client(self):
        return self.client

    def start(self):
        print('(Press Ctrl+C to stop this)')
        self.client.run_until_disconnected()


if __name__ == '__main__':
    data_storage_path = config().getpath()
    logger = get_logger(__name__, 'INFO')

    t = tg_watchon_class()

    p_list = []

    history = (
        ('https://t.me/tanhuaba', 1525, 999),
        ('https://t.me/sexinchina', 29434, 999),
        # ('https://t.me/joinchat/v22MnDcDTjoyZTdl', 1, 999)
    )
    for xx in history:
        p_list.append(Process(target=history_download(
            xx[0], xx[1], xx[2], t.get_client())))
        # p_list.append(tg_download_class(xx[0],xx[1],xx[2]))

    p_list.append(Process(target=t.start()))
    # 独立启动监听
    for xx in p_list:
        xx.start()
    for xx in p_list:
        xx.join()
