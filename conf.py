import random
import time
from os import getcwd, path


class config:
    def __init__(self):
        # 输出路径

        self._path = path.join(getcwd(), 'data_online')
        self.picture_storage_path = path.join(getcwd(), 'data_pic')

    def get_api(self):
        return 000000  # api_id

    def get_api_hash(self):
        return ''  # api_hash

    def getpath(self):
        return self._path

    def get_pic_path(self):
        return self.picture_storage_path

    def get_whiltlist(self):
        return {
            'chats': (499447099,),  # 监听的聊天id
            'channels': (1367105868, 1328305860)  # 监听的频道id
        }

    def get_history(self):
        return (
            ('https://t.me/aaaa', 1525, 999),  #下载的第一个频道的分享链接，开始消息id，下载消息数量
            ('https://t.me/bbbb', 29434, 999), #下载的第二个频道的分享链接，开始消息id，下载消息数量
            # 更多下载链接请自行添加
        )

    def get_random_file_name(self):
        H = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        salt = ''
        for i in range(22):
            salt += random.choice(H)
        t_dir = time.strftime("%Y-%m-%d", time.localtime())
        return salt
