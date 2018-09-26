#!/usr/bin/env python3
"""import logging
logging.basicConfig(handlers=[logging.StreamHandler(), logging.FileHandler('test.log', 'w', 'utf-8')],
                             format=u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s',
                             level=logging.INFO)
"""

import time
import requests

from vkontakte import botvk, users

from EventSender import event_sender



vk = botvk
while True:
    try:
        # Проверяем сообщения в вк
        vk.get_messages()
        # И в других клиентах ...

        # проверяем события
        event_sender.check()
    except KeyboardInterrupt:
        break
    # Ошибка времени(бывает всегда)
    except requests.exceptions.ConnectionError:
        print ("Ловим разрыв соединения, ждем чуда")
        time.sleep(5)
    except requests.exceptions.ReadTimeout:
        print("Ловим разрыв соединения, ждем чуда")
        time.sleep(5)

    #except Exception as exp:
     #   vk.send_message("25624369", "Ошибка: %s" % str(exp))
     #   raise SystemExit

users.destruct()
# Выходная часть
print ("Сохранено")


