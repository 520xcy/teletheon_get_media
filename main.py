from telethon import TelegramClient, sync, errors, events, utils
from telethon.tl.types import PeerChannel, MessageMediaWebPage, PeerChat, InputPeerUser
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
import shelve
from log import get_logger


class tg_watchon_class:

    def __init__(self, project_path):

        self.project_path = project_path
        self.data_storage_path = os.path.join(self.project_path, 'data_online')
        self.historydb = os.path.join(self.project_path, 'history.shelve')
        self.conf = self.get_conf()
        self.api_id = self.conf['api']
        self.api_hash = self.conf['api_hash']
        self.watchchannel = []
        self.watchuser = []
        self.myid = 0

        self.download = []

        if not os.path.exists(self.data_storage_path):
            os.mkdir(self.data_storage_path)

        if self.conf['proxyhost'] and self.conf['proxyport']:
            self.client = TelegramClient('some_name', self.api_id, self.api_hash,
                                         proxy=(socks.SOCKS5, self.conf['proxyhost'], self.conf['proxyport'])).start()
        else:
            self.client = TelegramClient(
                'some_name', self.api_id, self.api_hash).start()

        self.myid = self.client.get_me().id

        self.admin_id = (self.client.get_entity(self.conf['admin_id'])).id if isinstance(
            self.conf['admin_id'], str) else self.conf['admin_id'] if self.conf['admin_id'] else 0

        self.forward_channel = (self.client.get_entity(
            self.conf['forward_channel'])).id if isinstance(self.conf['forward_channel'], str) else self.conf['forward_channel'] if self.conf['forward_channel'] else 0

        self.error_notice = (self.client.get_entity(
            self.conf['error_notice'])).id if isinstance(self.conf['error_notice'], str) else self.conf['error_notice'] if self.conf['error_notice'] else 0

        for wlt in self.conf['watchchannel']:
            self.watchchannel.append((self.client.get_entity(
                wlt)).id if isinstance(wlt, str) else wlt)

        for wlu in self.conf['watchuser']:
            self.watchuser.append((self.client.get_entity(
                wlu)).id if isinstance(wlu, str) else wlu)

        @self.client.on(events.NewMessage)
        async def handler(event):
            # print("handler init success")
            # print('sender: ' + str(event.input_sender) + 'to: ' + str(event.message.to_id))
            logger.info(
                f'sender: {str(event.input_sender)} to: {str(event.message.to_id)} event: {str(event)}')

            from_id = event.from_id.user_id if str(
                event.from_id).startswith('PeerUser') else None

            to_id = event.message.to_id.user_id if str(
                event.message.to_id).startswith('PeerUser') else None

            if from_id == self.admin_id and to_id == self.myid:
                await self.text_command(event)
                return

            if from_id in self.watchuser and event.media is not None:
                await self.media_download(entity_id=from_id, event=event, is_user=True)
                return

            if event.fwd_from is not None:
                from_id = event.fwd_from.saved_from_peer.channel_id if str(
                    event.fwd_from.saved_from_peer).startswith('PeerChannel') else None
                if from_id in self.watchchannel and event.media is not None:
                    await self.media_download(entity_id=from_id, event=event, is_savefrom=True)

            from_id = event.peer_id.channel_id if str(
                event.peer_id).startswith('PeerChannel') else None

            if from_id in self.watchchannel and event.media is not None:
                await self.media_download(entity_id=from_id, event=event)

    async def history_download(self, chat_id, offset_id: int, limit: int):
        entity = await self.client.get_entity(chat_id)
        for ids in range(offset_id, offset_id+limit):
            event = await self.client.get_messages(entity, ids=ids)
            try:
                if event.media is not None:
                    await self.media_download(entity_id=entity.id, event=event, history=True, need_forward=False)
            except:
                pass

        # async for event in self.client.iter_messages(entity, offset_id=offset_id, reverse=True, limit=limit):
        #     try:
        #         if event.media is not None:
        #             await self.media_download(entity_id=entity.id, event=event, history=True, need_forward=False)
        #     except:
        #         pass

    async def media_download(self, entity_id, event, history=False, need_forward=True, is_user=False, is_savefrom=False):
        try:
            offset = 0
            file_name = self.get_filename(event, is_user, is_savefrom)
            if file_name == False:
                return False
            if need_forward and self.forward_channel:
                try:
                    if history:
                        await self.client.forward_messages(self.forward_channel, event)
                    else:
                        await self.client.forward_messages(self.forward_channel, event.message)
                except:
                    pass
            file_id = file_name[1]

            _dir = os.path.join(self.data_storage_path, str(entity_id))
            if not os.path.exists(_dir):
                os.makedirs(_dir)

            file_name = os.path.join(_dir, file_name[0])

            if not is_user and self.db_check(str(entity_id), file_id):
                logger.critical(f'数据库已存在:{file_name}')
                return False

            if os.path.isfile(file_name):
                logger.critical(f'文件已存在:{file_name}')
                return False

            if os.path.isfile(file_name+'.download'):
                offset = os.path.getsize(file_name+'.download')

            logger.critical(f'Start Download File: {file_name}')
            try:
                self.download.append(file_name)
                print(offset)
                with open(file_name+'.download', 'ab+') as fd:
                    async for chunk in self.client.iter_download(event.media, offset=offset):
                        fd.write(chunk)
                # await self.client.download_media(event.media, file_name)
            except Exception as e:
                # os.remove(file_name)
                logger.error(f'{e},{entity_id}:{file_name}')
                raise
            else:
                os.rename(file_name+'.download', file_name)
                logger.critical(f'Finish Download File: {file_name}')
                if not is_user:
                    self.db_write(str(entity_id), file_id)
            finally:
                self.download.remove(file_name)
        except Exception as e:
            if self.error_notice:
                try:
                    if history:
                        await self.client.forward_messages(self.error_notice, event)
                    else:
                        await self.client.forward_messages(self.error_notice, event.message)
                    await self.client.send_message(self.error_notice, f'error: {e},user: {entity_id} - {event.id}')
                except:
                    pass
            raise
        else:
            return True

    async def text_command(self, event):
        # sender = await event.get_sender()
        # logger.error(f'entity.id: {entity.id}')

        raw_text = event.raw_text.strip()
        if raw_text.strip().startswith('/history'):
            self.conf = self.get_conf()
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
            if len(xx) < 4:
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
        elif raw_text.startswith('/show'):
            try:
                command = raw_text.split(' ')
                url = command[1]
                offset_id = int(url[url.rindex('/')+1:]) - 1
                _entity = url[0:url.rindex('/')]
                eid = _entity[_entity.rindex('/')+1:]
                if eid.isdigit():
                    entity = await self.client.get_entity(int(eid))
                else:
                    entity = await self.client.get_entity(_entity)
                async for msg in self.client.iter_messages(entity, offset_id=offset_id, reverse=True, limit=1):
                    await event.reply(str(msg))
            except:
                await event.reply(f'命令格式错误 /show 消息链接')
                raise

        elif raw_text.startswith('/help'):
            await event.reply(f'/download 频道链接 开始id 数量 下载指定频道历史媒体文件\n/history 下载配置中频道历史文件\n/reload 重载config.json文件(api设置重载无效)\n/cfg 显示当前配置\n/status 显示任务下载状态\n/show 显示信息详情')
            return
        elif raw_text.startswith('/reload'):
            self.conf = self.get_conf()
            await self.init_conf()
            await event.reply(f'重载config.json')
        elif raw_text.startswith('/cfg'):
            msg = str(self.__dict__)
            strlist = self.cut_text(msg, 4095)
            for r in strlist:
                await event.reply(r)
        elif raw_text.startswith('/status'):
            msg = str(self.download)
            strlist = self.cut_text(msg, 4095)
            for r in strlist:
                await event.reply(r)
        else:
            await event.reply(str(event))

    async def init_conf(self):
        self.watchchannel = []
        self.watchuser = []
        self.admin_id = (await self.client.get_entity(self.conf['admin_id'])).id if isinstance(
            self.conf['admin_id'], str) else self.conf['admin_id'] if self.conf['admin_id'] else 0

        self.forward_channel = (await self.client.get_entity(
            self.conf['forward_channel'])).id if isinstance(self.conf['forward_channel'], str) else self.conf['forward_channel'] if self.conf['forward_channel'] else 0

        self.error_notice = (await self.client.get_entity(
            self.conf['error_notice'])).id if isinstance(self.conf['error_notice'], str) else self.conf['error_notice'] if self.conf['error_notice'] else 0

        for wlt in self.conf['watchchannel']:
            self.watchchannel.append((await self.client.get_entity(
                wlt)).id if isinstance(wlt, str) else wlt)

        for wlu in self.conf['watchuser']:
            self.watchuser.append((await self.client.get_entity(
                wlu)).id if isinstance(wlu, str) else wlu)

    def get_filename(self, event, is_user=False, is_savefrom=False):
        file_name = ''
        if event.document:
            try:
                if type(event.media) == MessageMediaWebPage:
                    return False
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

        _file_name, _extension = os.path.splitext(file_name)
        event_id = event.fwd_from.saved_from_msg_id if is_savefrom else event.id
        if is_user:
            file_name = f'{self.format_filename(_file_name)}{_extension}'
        else:
            file_name = f'{event_id} - {self.format_filename(_file_name)}{_extension}'
        if any(self.str_find(file_name, _name) for _name in self.conf['filename_block']):
            return False
        else:
            return (file_name, event_id)

    def str_find(self, s: str, t: str):
        return s.find(t) >= 0

    def get_conf(self):
        with open(os.path.join(self.project_path, 'conf.json'), 'r', encoding='UTF-8') as r:
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

    def cut_text(self, text, lenth):
        textArr = re.findall('.{'+str(lenth)+'}', text)
        textArr.append(text[(len(textArr)*lenth):])
        return textArr

    def db_write(self, key, index):
        with shelve.open(self.historydb, writeback=True) as db:
            if key in db:
                db[key].append(index)
            else:
                db[key] = [index]

    def db_check(self, key, index):
        with shelve.open(self.historydb) as db:
            if key in db:
                if index in db[key]:
                    return True
            return False


if __name__ == '__main__':

    PROJECT_PATH = os.path.split(os.path.realpath(__file__))[0]
    logger = get_logger(__name__, 'ERROR')

    t = tg_watchon_class(PROJECT_PATH)
    t.start()
