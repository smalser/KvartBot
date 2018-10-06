#!/usr/bin/env python3
token = open("token.txt", "r").read().strip()

import threading, datetime, time, json, re
import vk, requests
import DataBase as db
from smiles import smiles


# Глобальная дома!
# глобальная юзеры!
users = db.DB_users_vk
doma = db.DB_doma

# Ругулярка для емейла
regx_email=r"[\w\d\._-!#$%&'\*\+-/=\?^_`{}|~]+@?[\w\d\_\-]+\.+[\w\d\_\-]+"
########################################################################################################################
# Класс обработчика вк
class BotVk:
    # Получаем доступ по токену
    def __init__(self):
        print("Авторизируемся в ВК")
        try:
            self.vk_api = vk.API(vk.Session(token),version="5") # Само апи
            print("    Успешно")
        except Exception as exp:
            print("Ошибка!", exp)
            print(token)
        self.lasttime = time.time()

    # Деструктор
    def __del__(self):
        print("Дропаем вк")

    # Следим за нормой 3 запроса в секунду (кроме экзекута)
    def api(self, timer=0.34):
        if (time.time() < self.lasttime):
            #log.debug("Спешим в апи, ждем")
            time.sleep(self.lasttime - time.time())
        self.lasttime = time.time() + timer +0.05
        return self.vk_api

    def reload_api(self):
        self.vk_api = vk.API(vk.Session(token), version="5")  # Само апи

    # Получаем сообщения
    def get_messages(self):
        messages = []
        tmp_txt = """
            var besedas = API.messages.getConversations({"filter":"unread"});
            var msgs = [];
            
            var i=1;
            while ((i < besedas.length-1) && (i < 20)){
                var a = API.messages.getHistory({"user_id":besedas[i]["conversation"]["peer"]["id"], "count": 1})[1];
                msgs.push(a);
                i = i+1;
            };
            return msgs;
        """
        messages = self.api(1).execute(code=tmp_txt.replace("    ",""))
        if messages:
            print("Сообщения", messages)

        for i in messages:
            self.choose_message_all(i)

    # Выбор куда идти на первых шагах
    def choose_message_all(self, msg, *args):
        id = str(msg["uid"])
        # Если пользователя нет в базе
        if id not in users:
            print("Новый пользователь", id)
            users[id] = None
            self.send_message(id, first_message(msg))

        # Если мы меняем свой тип!
        elif smiles.swap in msg["body"]:
            users[id].type = None
            self.send_message(id, first_message(msg))

        # Если он еще не авторизировался
        elif not users[id]:
            self.send_message(id, registry_message(msg))

        # Если у нас не указан тип
        elif not users[id].type:
            print (users[id].type)
            self.send_message(id, registry_message(msg))

        # Ну и все остальные
        else:
            if users[id].type == "arendator":
                self.choose_message_arendator(msg)
            elif users[id].type == "client":
                self.choose_message_client(msg)

    # Выбор куда отправить пользователя
    def choose_message_arendator(self, msg, *args):
        id = str(msg["uid"])
        user = users[id]
        txt = msg["body"].lower()
        print("Пользвоатель %s в меню %s" % (id, user.menu))

        # Если он хочет вернуться - кидаем его в меню
        if "⬅" in txt:
            user.menu = "menu"
            user.extra = None
            self.send_message(id, arendator_menu(msg))
            return

        # Если он сейчас в меню
        elif user.menu == "menu" or not user.menu:
            # Добавление квартиры
            if smiles.add in txt:
                user.menu = "add_flat"
                user.extra = {}
                self.send_message(id, arendator_add_flat(msg))
                return
            # Изменение квартиры
            elif smiles.change in txt:
                user.menu = "change_flat"
                self.send_message(id, arendator_change_flat(msg))
                return
            # Удаление квартиры
            elif smiles.delete in txt:
                user.menu = "delete_flat"
                self.send_message(id, arendator_delete_flat(msg))
                return
            # Настройка уведомлений
            elif smiles.notification in txt:
                user.menu = "edit_notifications"
                user.extra = None
                self.send_message(id, arendator_edit_notifications(msg))
                return
                # Настройки квартиранта
            elif smiles.kvartirant in txt and user.extra:
                dom = doma[user.doma[user.extra["name"]]]
                print(dom.kvartirant)
                if dom.kvartirant:
                    user.menu = "change_kvartirant"
                    self.send_message(id, arendator_add_kvartirant(msg, False))
                else:
                    user.menu = "add_kvartirant"
                    self.send_message(id, arendator_add_kvartirant(msg))
                return
            # Подтверждение оплаты
            elif smiles.checked in txt:
                r = user.confirm_oplata()
                if r:
                    self.send_message(id, arendator_view_flat(msg, "Оплата подтверждена"))
                    return
                else:
                    user.menu = "menu"
                    user.extra = None
                    self.send_message(id, arendator_menu(msg, "Ошибка, попробуйте еще раз."))
                    return

            # TODO
            #
            # Если он ввел номер дома
            else:
                z = 99999
                try:                # Пробуем получить инт
                    print("Парсим сообщение", txt)
                    z = int(txt)
                except:             # Если не вышло
                    print("Пользователь неправильно ввел номер")
                    self.send_message(id, arendator_menu(msg), "Ошибка ввода!\n")
                    return

                # Если у пользователя есть дом с таким номером
                if z <= len(user.doma):
                    name = tuple(user.doma.keys())[z - 1]
                    user.extra = {"name": name}
                    print("Экстра пользователя ", user.extra)
                    self.send_message(id, arendator_view_flat(msg))
                    return
                # Если нет
                else:
                    self.send_message(id, arendator_menu(msg), "У вас нет квартиры под номером %d\n" % z)
                    return

        # Добавление квартиры
        elif user.menu == "add_flat":
            print("Добавление квартиры пользователем ", id)
            self.send_message(id, arendator_add_flat(msg))
            return

        # Изменение квартиры
        elif user.menu == "change_flat":
            print("Изменение квартиры пользователем ", id)
            if not user.doma:
                self.send_message(id, arendator_menu(msg, "У вас нет квартир для редактирования."))
                return
            self.send_message(id, arendator_change_flat(msg))
            return

        # Удаление
        elif user.menu == "delete_flat":
            print("Удаление квартиры пользователем ", id)
            if not user.doma:
                self.send_message(id, arendator_menu(msg, "У вас нет квартир для удаления."))
            self.send_message(id,arendator_delete_flat(msg))
            return

        # Добавление квартиранта
        elif user.menu == "add_kvartirant":
            print("Добавление квартиранта пользователем ", id)
            self.send_message(id, arendator_add_kvartirant(msg))
            return

        # Изменение квартиранта
        elif user.menu == "change_kvartirant":
            print("Изменение квартиранта пользователем ", id)
            self.send_message(id, arendator_add_kvartirant(msg, False))
            return

        # Управление уведомлениями
        elif user.menu == "edit_notifications":
            print("Изменение уведомлений пользователем ", id)
            self.send_message(id, arendator_edit_notifications(msg))
            return

        #ИВЕНТЫ!!
        # Ивент об оплате
        elif user.menu == "event_oplata":
            print("Ивент оплаты пользователем ", id)
            self.send_message(id, arendator_event_oplata(msg))
            return

        # Ивент окончания договора
        elif user.menu == "event_end_date":
            print("Ивент окончания даты пользователем ", id)
            self.send_message(id, arendator_event_end_date(msg))
            return

        # Если ничего не подошло
        self.send_message(id, arendator_menu(msg))
        return

    # Выбор для клиента
    def choose_message_client(self, msg, *args):
        id = str(msg["uid"])
        user = users[id]
        txt = msg["body"].lower()

        # Если он хочет вернуться - кидаем его в меню
        if "⬅" in txt:
            user.menu = "menu"
            user.extra = None
            self.send_message(id, client_menu(msg))
            return

        # Выбор куда идти
        elif user.menu == "menu":
            if smiles.add in txt:
                if not user.kvartiri:
                    user.menu = "add_kvartira"
                    user.extra = None
                    self.send_message(id, client_add_kvartira(msg))

                else:
                    self.send_message(id, client_menu(msg, "У вас уже есть квартира"))
                return

            elif smiles.copy in txt:
                user.menu = "copy_kvartira"
                user.extra = None
                self.send_message(id, client_copy_kvartira(msg))
                return

            elif smiles.change in txt:
                if user.kvartiri:
                    user.menu = "change_kvartira"
                    user.extra = None
                    self.send_message(id, client_add_kvartira(msg, False))
                else:
                    self.send_message(id, client_menu(msg, "У вас еще нет квартиры"))
                return

            elif smiles.delete in txt:
                if user.kvartiri:
                    user.menu = "delete_kvartira"
                    user.extra = None
                    self.send_message(id, client_delete_kvartira(msg))
                else:
                    self.send_message(id, client_menu(msg, "У вас нет квартиры для удаления"))
                return

            # Настройка уведомлений
            elif smiles.notification in txt:
                user.menu = "edit_notifications"
                self.send_message(id, client_edit_notifications(msg))
                return

            # Настройка оплаты
            elif smiles.money in txt:
                user.menu = "edit_money"
                self.send_message(id, client_edit_money(msg))
                return

            elif smiles.checked in txt and user.kvartiri:
                user.confirm_oplata()
                self.send_message(id, client_menu(msg,"оплата успешно подтверждена!"))
                return

        elif user.menu == "add_kvartira":
            self.send_message(id, client_add_kvartira(msg))
            return

        elif user.menu == "copy_kvartira":
            self.send_message(id, client_copy_kvartira(msg))
            return

        elif user.menu == "change_kvartira":
            self.send_message(id, client_add_kvartira(msg, False))
            return

        elif user.menu == "delete_kvartira":
            self.send_message(id, client_delete_kvartira(msg))
            return

        # Управление уведомлениями
        elif user.menu == "edit_notifications":
            print("Изменение уведомлений пользователем ", id)
            self.send_message(id, client_edit_notifications(msg))
            return

        # Управление оплатой
        elif user.menu == "arendator_edit_money":
            print("Изменение оплаты пользователем ", id)
            self.send_message(id, client_edit_money(msg))
            return

        # ИВЕНТЫ!!
        # Ивент об оплате
        elif user.menu == "event_oplata":
            print("Ивент оплаты пользователем ", id)
            self.send_message(id, client_event_oplata(msg))
            return

            # Ивент окончания договора
        elif user.menu == "event_end_date":
            print("Ивент окончания даты пользователем ", id)
            self.send_message(id, client_event_end_date(msg))
            return

        #TODO
        # Типа если ничего
        self.send_message(id, client_menu(msg))
        return

    # Просто отправка сообщения
    def send_message(self, id, arg, addmess="", *args):
        print("Отправляем пользователю ", id, " сообщение: ", arg)
        self.api().messages.send(user_id=id,
                                 message=addmess+"\n\n"+arg["message"] if "message" in arg else None,
                                 keyboard=arg["keyboard"] if "keyboard" in arg else None,
                                 attachment = arg["attachments"] if "attachments" in arg else None
                                 )

    # Функция расписки вложений из вк
    @staticmethod
    def parse_images(msg):
        images = []
        # Размеры и функция выбора лучшего размера
        sizes = ('src_xxbig', 'src_xbig', 'src_big', 'src')

        attachments = msg["attachments"]
        print("Парсим атачмент ", attachments)
        best = None
        for i in attachments:
            if i["type"] == "photo":
                img = i["photo"]
                for s in sizes:
                    if s in img:
                        best = img[s]
                        break
                if best:
                    images.append(best)
        print("Картинки: ", images)
        return images

    # Тут загружаются картинки в лс
    def upload_images(self, msg, imgs):
        print("Выкачиваем фото")
        r = self.api().photos.getMessagesUploadServer(peer_id=msg["uid"])
        att = []
        for i, k in enumerate(imgs):
            with open("1.jpg", "wb") as f:
                f.write(requests.get(k).content)
            req = requests.post(r["upload_url"], files={"photo":open("1.jpg", "rb")}).json()
            phot = self.api().photos.saveMessagesPhoto(**req)[0]
            print (phot)
            att.append(phot["id"])

        print("    Успешно")
        return att


##################################
botvk = BotVk()


choose_message_keyboard = json.dumps(
    {
        "one_time": True,
        "buttons": [
          [{
            "action": {
              "type": "text",
              "label": "1. Я снимаю квартиру"
            },
            "color": "primary"
          }],
         [{
            "action": {
              "type": "text",
              "label": "2. Я арендодатель"
            },
            "color": "primary"
          }],
        ]
    },ensure_ascii=False)
# Добавление пользователя
def first_message(message, *args):
    # добавляем в базу
    id = str(message["uid"])

    # Мы просто отправляем сообщение с приветствием
    return {"message": "Привет, я бот управления квартирой, выбери кто ты:"+
                       "\n(Бот использует преподготовленные кнопки, для работы используйте официальные версии ВКонтакте)",
            "keyboard": choose_message_keyboard}

# Стандартное меню арендатора
arendator_menu_keyboard = json.dumps(
    {
        "one_time": True,
        "buttons": [
          [{
            "action": {
              "type": "text",
              "label": smiles.add + " Добавить квартиру"
            },
            "color": "primary"
          }],
         [{
            "action": {
              "type": "text",
              "label": smiles.change +" Изменить квартиру"
            },
            "color": "default"
          },
         {
            "action": {
              "type": "text",
              "label": smiles.delete + " Удалить квартиру"
            },
            "color": "default"
          }],
         [#{
           # "action": {
           #   "type": "text",
           #   "label": smiles.money + " Настройки оплаты"
           # },
           # "color": "default"
           # },
             {
                 "action": {
                     "type": "text",
                     "label": smiles.notification + " Настройки уведомлений"
                 },
                 "color": "default"
             }
         ],
            [{
                "action": {
                    "type": "text",
                    "label": smiles.swap + " Сменить меню"
                },
                "color": "default"
            }]
        ]},
    ensure_ascii=False) # Это чтобы жсон правильно кодировался
# меню арендатора
def arendator_menu(message, addmsg="", *args):
    id = str(message["uid"])
    user = users[id]

    # Выводим квартиры
    message = "*МЕНЮ АРЕНДОДАТЕЛЯ* \nВаши квартиры:\n"
    if not user.doma:
        message += smiles.tab+"Вы еще не добавили квартиры."
    else:
        for i, k in enumerate(user.doma):
            message += smiles.tab + "%d. %s\n" % (i+1, k)
        message += "Введите номер квартиры чтобы посмотреть полную информацию.\n"
    message += "\nВы можете добавить, редактировать или удалить квартиру."

    # Выводим
    return {"message": addmsg+"\n\n"+message, "keyboard": arendator_menu_keyboard}


# Меню клиента
def client_menu(message, addmsg="", *args):
    id = str(message["uid"])
    user = users[id]

    message = "*МЕНЮ СНИМАЮ КВАРТИРУ*\n"
    if user.kvartiri:
        message += "Снимаемая вами квартира\n" + str(user.kvartiri)
        keyboard = json.dumps(
            {
                "one_time": True,
                "buttons": [
                    [{
                            "action": {
                                "type": "text",
                                "label": smiles.checked + " Подтвердить оплату"
                            },
                            "color": "positive"
                    }],
                    [{
                        "action": {
                            "type": "text",
                            "label": smiles.change + " Изменить снимаемую квартиру"
                        },
                        "color": "default"
                    },
                        {
                        "action": {
                            "type": "text",
                            "label": smiles.delete + " Удалить снимаемую квартиру"
                        },
                        "color": "default"
                    }],
                    [{
                        "action": {
                            "type": "text",
                            "label": smiles.money + " Настройки оплаты"
                        },
                        "color": "default"
                    },
                        {
                            "action": {
                                "type": "text",
                                "label": smiles.notification + " Настройки уведомлений"
                            },
                            "color": "default"
                        }
                    ],
                    [{
                        "action": {
                            "type": "text",
                            "label": smiles.swap + " Сменить меню"
                        },
                        "color": "default"
                    }]
                ]},
            ensure_ascii=False)
    else:
        message += "Вы еще не снимаете квартиру\nВы можете добавить снимаемую квартиру"
        keyboard = json.dumps(
            {
                "one_time": True,
                "buttons": [
                    [{
                        "action": {
                            "type": "text",
                            "label": smiles.add + " Добавить снимаемую квартиру"
                        },
                        "color": "primary"
                    }],
                    [{
                        "action": {
                            "type": "text",
                            "label": smiles.copy + " Импорт с аккаунта арендодателя"
                        },
                        "color": "primary"
                    }],
                    [{
                        "action": {
                            "type": "text",
                            "label": smiles.notification + " Настройка уведомлений"
                        },
                        "color": "default"
                    }],
                    [{
                        "action": {
                            "type": "text",
                            "label": smiles.swap + " Сменить меню"
                        },
                        "color": "default"
                    }]
                ]},
            ensure_ascii=False)


    return {"message": addmsg + "\n\n" + message, "keyboard": keyboard}


# Регистрация после первого захода
def registry_message(message, *args):
    id = str(message["uid"])
    text = message["body"].lower()

    if "2." in text:                     # Если арендатор
        if not users[id]:
            users[id] = db.Arendator.Create(id, "vk")
        else:
            users[id].type = "arendator"
            users[id].extra = None
            users[id].menu = "menu"
            # users[id].db_update() Типа так выгрузим изщ памяти старый образец
            users.dump(id)

        return arendator_menu(message)

    elif "1." in text:                     # Если клиент
        if not users[id]:
            users[id] = db.Client.Create(id, "vk")
        else:
            users[id].type = "client"
            users[id].extra = None
            users[id].menu = "menu"
            #users[id].db_update() Типа так выгрузим изщ памяти старый образец
            users.dump(id)
        return client_menu(message)

    else:
        return {"message": "Пожалуйста выбери из предложенных кнопок, кем ты являешься",
                "keyboard": choose_message_keyboard}

########################################################################################################################
# Меню арендатора
########################################################################################################################
# Аргументы добавления дома
arendator_add_flat_args = ("name", "adress", "square", "rooms", "sanuzel", "extras", "text", "photos")
# Тексты для запросов
arendator_add_flat_args_text ={
    "name": "Введите название квартиры, которое останется неизменным (Например: Квартира на подлужной)",
    "adress": "Введите адрес квартиры (Например: Россия, г. Москва, ул. Пушкина д 12, кв 8)",
    "flat": "Введите номер этажа цифрой (Например: 3)",
    "square": "Введите площадь квартиры (Например: 65.5)",
    "rooms": "Введите кол-во комнат, где 0-студия (Например: 2)",
    "sanuzel": "Введите тип санузла, где 0 совместный, 1 раздельный, n-несколько санузлов (Например 2)",
    "extras": """Введите удобства буквами через пробел, где:
    х - холодильник
    с - стиральная машина
    к - кондиционер
    т - телевизор
    и - микроволновка
    в - приточная вентиляция
    п - посудомоечная машина
    м - мебель
    о - вид из окон
    (Например: с к х м о) 
    """,
    "text": "Введите дополнительное текстовое описание (Например: удобное расположение от метро, тихий район итд...)",
    "photos": "Прикрепите фотографию."
}

# Клавиатура для добавления квартиры
arendator_add_flat_keyboard = json.dumps({
        "one_time": False, "buttons": [
  [{
    "action": {
      "type": "text",
      "label": smiles.next + " Пропустить шаг"
    },
    "color": "default"
  }],
  [{
    "action": {
      "type": "text",
      "label": smiles.back + " Отменить"
    },
    "color": "negative"
  },

   {
    "action": {
      "type": "text",
      "label": smiles.done + " Закончить"
    },
    "color": "positive"
  }
   ]]},ensure_ascii=False)

# Добавление квартиры
def arendator_add_flat(msg, *args):
    id = str(msg["uid"])
    user = users[id]
    txt = msg["body"].lower()

    # Если еще не начали вводить - добавляем
    if not user.extra:
        user.extra = {"name":""}
        return {"message": arendator_add_flat_args_text["name"], "keyboard":json.dumps({
                "one_time": True, "buttons": [
          [{
            "action": {
              "type": "text",
              "label": "⬅ Вернуться"
            },
            "color": "negative"
          }]]},
        ensure_ascii=False)}

    # Если все готово
    elif smiles.done in txt:
        user.add_dom()
        return arendator_view_flat(msg,"Квартира успешно добавлена!")

    # Иначе
    else:
        # Находим где мы сейчас
        zis, next = arendator_add_flat_args[-1], None
        for i in reversed(arendator_add_flat_args):
            if i in user.extra:
                zis = i
                break
            next = i
        print (zis, next)

        # Если пропускаем
        if smiles.next in txt:
            user.extra[zis] = False
        # Если это добавление фоток
        elif zis == "photos":
            if "attachments" in msg:
                user.extra[zis] = BotVk.parse_images(msg)
            else:
                return {"message": "В вашем сообщении нет фото\n" + arendator_add_flat_args_text[zis],
                        "keyboard": arendator_add_flat_keyboard}
        # Иначе просто текст
        else:
            user.extra[zis] = txt

        # Если это последний аргумент
        if zis == arendator_add_flat_args[-1]:
            user.add_dom()
            return arendator_view_flat(msg, "Квартира успешно добавлена!")

        # Если не последний продолжаем
        user.extra[next] = ""
        # Выводим его описание
        return {"message": arendator_add_flat_args_text[next], "keyboard":arendator_add_flat_keyboard}

# Показ описания квартиры
def arendator_view_flat(msg, add_msg="", *args):
    id = str(msg["uid"])
    user = users[id]
    name = user.extra["name"]
    dom = doma[user.doma[name]] # Дом

    att = None
    if dom.photos:
        att = botvk.upload_images(msg,dom.photos)


    if dom.kvartirant:
        return {"message": add_msg + "\n\n" + str(dom), "attachments": att, "keyboard": json.dumps({
        "one_time": True, "buttons": [
            [
               {
                "action": {
                    "type": "text",
                    "label": smiles.kvartirant + " Изменение/удаление квартиранта"
                },
                "color": "primary"
            }],
            [{
                "action": {
                    "type": "text",
                    "label": smiles.checked + " Подтвердить оплату"
                },
                "color": "positive"
            }],
            [{
                "action": {
                    "type": "text",
                    "label": smiles.change + " Изменить квартиру"
                },
                "color": "default"
            }],
            [{
                "action": {
                    "type": "text",
                    "label": smiles.back + " Назад"
                },
                "color": "default"
            }]
            ]}, ensure_ascii=False)}
    else:
        return {"message": add_msg + "\n\n" + str(dom), "attachments": att, "keyboard": json.dumps({
            "one_time": True, "buttons": [
                [
                    {
                        "action": {
                            "type": "text",
                            "label": smiles.kvartirant + " Добавление квартиранта"
                        },
                        "color": "primary"
                    }
                ],
                [{
                    "action": {
                        "type": "text",
                        "label": smiles.change + " Изменить квартиру"
                    },
                    "color": "default"
                }],
                [{
                    "action": {
                        "type": "text",
                        "label": smiles.back + " Назад"
                    },
                    "color": "default"
                }]
            ]}, ensure_ascii=False)}


def arendator_change_flat(msg, *args):
    id = str(msg["uid"])
    user = users[id]

    if user.extra:             # Если номер введен
        return arendator_change_flat_main(msg)

    # Вывод квартир
    message = "Введите номер квартиры для редактирования:\n"
    for i, k in enumerate(user.doma):
        message += smiles.tab + "%d. %s\n" % (i + 1, k)

    ret = {"message": message, "keyboard": json.dumps({
        "one_time": True, "buttons": [
            [{
                "action": {
                    "type": "text",
                    "label": smiles.back + " Назад"
                },
                "color": "default"
            }]]}, ensure_ascii=False)}
    #
    try:                                    # Пробуем сделать инт
        z = int(msg["body"])
    except:                                 # Если не выходит пишем ввести квартиру
        if user.extra:
            ret["message"] = "Ошибка ввода!\n"+ret["message"]
        return ret

    if z <= len(user.doma):
        user.extra = {"name": tuple(user.doma.keys())[z-1]}
        return arendator_change_flat_main(msg)
    else:
        ret["message"] = "У вас нет квартиры с номером %d" % z + ret["message"]
    return ret

# Вопросная часть изменения квартиры
def arendator_change_flat_main(msg, *args):
    id = str(msg["uid"])
    user = users[id]
    txt = msg["body"].lower()
    print(user.extra)
    name = user.extra["name"]
    dom = doma[user.doma[name]]  # Дом

    # Если мы имеем только имя - просим адрес
    if len(user.extra) == 1:
        user.extra["adress"] = ""
        return {"message": arendator_add_flat_args_text["adress"] +
                           "\n(Прошлое значение: %s)" % dom.adress,
                "keyboard": arendator_add_flat_keyboard} # Та же клавиатура

    # Если все готово
    elif smiles.done in txt:
        user.change_dom()
        return arendator_view_flat(msg, "Квартира успешно изменена!")

    # Или спрашиваем дальше все по списку
    else:
        # Вычисляем на каком мы аргументе
        zis, next = arendator_add_flat_args[-1], None
        for i in reversed(arendator_add_flat_args[1:]):
            if i in user.extra:
                zis = i
                break
            next = i
        print(zis, next)

        # Если пропуск
        if smiles.next in txt:
            # Оставляем то же самое
            user.extra[zis] = False
        # Если это добавление фоток
        elif zis == "photos":
            if "attachments" in msg:
                user.extra[zis] = BotVk.parse_images(msg)
            else:
                user.extra[zis] = "delet"
        # Иначе просто текст
        else:
            user.extra[zis] = txt

        # Если это последний аргумент
        if zis == arendator_add_flat_args[-1]:
            user.change_dom()
            return arendator_view_flat(msg, "Квартира успешно изменена!")

        # Если не последний продолжаем
        user.extra[next] = ""
        # Если экстра записываем предыдущие значения
        if next == "extras":
            a = ""
            for i in dom.extras:
                if dom.extras[i]:
                    a += smiles.extras[i] + " "
            txt = arendator_add_flat_args_text[next]+("\n(Прошлое значение: %s)" % a)
        else:
            txt = arendator_add_flat_args_text[next]+("\n(Прошлое значение: %s)" % dom.__dict__[next])
        txt = txt.replace("False", "не указано").replace("None", "не указано")
        return {"message": txt, "keyboard": arendator_add_flat_keyboard}

# Удаление квартиры
def arendator_delete_flat(msg, *args):
    id = str(msg["uid"])
    user = users[id]

    # Если у нас уже есть начало
    if user.extra:
        # Есть ли конфирм
        if "confirm" in user.extra:
            # Если согласны на удаление
            if smiles.delete in msg["body"]:
                user.delete_dom()
                user.menu = "menu"
                user.extra = None
                return arendator_menu(msg,"Квартира удалена!")
            # Если нет то нас выкинет стрелкой
            # Иначе спрашиваем
            else:
                return arendator_delete_flat_confirm(msg)

    message = "Введите номер квартиры которую хотите УДАЛИТЬ:\n"
    for i, k in enumerate(user.doma):
        message += smiles.tab + "%d. %s\n" % (i + 1, k)

    ret = {"message": message, "keyboard": json.dumps({
        "one_time": True, "buttons": [
            [{
                "action": {
                    "type": "text",
                    "label": smiles.back + " Назад"
                },
                "color": "default"
            }]]}, ensure_ascii=False)}

    # Если только зашли
    if not user.extra:
        user.extra = {"name": ""}
        return ret
    # Иначе пробуем получить номер
    else:
        try:
            z = int(msg["body"])
        except:
            ret["message"] = "ошибка ввода!\n" + ret["message"]
            return ret

        # Это уже было кучу раз
        if z <= len(user.doma):
            user.extra["name"] = tuple(user.doma.keys())[z-1]
            user.extra["confirm"] = False
            return arendator_delete_flat_confirm(msg)
        else:
            ret["message"] = "У вас нет квартиры под номером %d\n" % z + ret["message"]
            return ret

# Подтверждение удаления квартиры
def arendator_delete_flat_confirm(msg):
    id = str(msg["uid"])
    user = users[id]
    name = user.extra["name"]

    return  {"message": "ВЫ УВЕРЕНЫ ЧТО ХОТИТЕ УДАЛИТЬ КВАРТИРУ '%s'\nЭто действие нельзя отменить" % name, "keyboard": json.dumps({
        "one_time": True, "buttons": [
            [{
                    "action": {
                        "type": "text",
                        "label": smiles.back + " Нет"
                    },
                    "color": "default"
                },
                {
                "action": {
                    "type": "text",
                    "label": smiles.delete + " Да"
                },
                "color": "negative"
            }]]}, ensure_ascii=False)}

# НАстройка уведомлений
def arendator_edit_notifications(msg):
    id = str(msg["uid"])
    user = users[id]
    txt = msg["body"]

    # Текущее значение
    nots = user.notifications[user.type]

    if smiles.done in txt:
        user.notifications[user.type] = True
        user.menu = "menu"
        user.db_update()
        return arendator_menu(msg, "Уведомления для арендодателя ВКЛЮЧЕНЫ")

    elif smiles.delete in txt:
        user.notifications[user.type] = False
        user.menu = "menu"
        user.db_update()
        return arendator_menu(msg, "Уведомления для арендодателя ВЫКЛЮЧЕНЫ")

    # Иначе выводим запрос
    txt = "Сейчас уведомления для арендодателя: *%s*" % ("ВКЛЮЧЕНЫ" if nots else "ВЫКЛЮЧЕНЫ")

    keyb = json.dumps({
        "one_time": False, "buttons": [
            [{
                "action": {
                    "type": "text",
                    "label": smiles.delete + " Выключить"
                },
                "color": "negative"
            },
                {
                    "action": {
                        "type": "text",
                        "label": smiles.done + " Включить"
                    },
                    "color": "positive"
            }],
            [{
                "action": {
                    "type": "text",
                    "label": smiles.back + " Отменить"
                },
                "color": "default"
            }
            ]]}, ensure_ascii=False)

    return {"message": txt, "keyboard": keyb}

# Продление договора
def arendator_dogovor(msg):
    id = str(msg["uid"])
    user = users[id]

    # TODO
    user.menu = "menu"
    return arendator_menu(msg, "Функция в разработке")

# ИВЕНТЫ!
# Когда нам пишло сообщение об оплате
def arendator_event_oplata(msg):
    id = str(msg["uid"])
    user = users[id]
    #dom = doma[user.doma[user.extra["name"]]]  # Дом
    txt = msg["body"]

    # Подтверждение оплаты
    if smiles.checked in txt:
        user.confirm_oplata()
        user.menu = "menu"
        return arendator_menu(msg, "Оплата подтверждена")
    # Отключение уведомлений
    elif smiles.delete in txt:
        user.notifications["arendator"] = False
        user.menu = "menu"
        user.extra = None
        user.db_update()
        return arendator_menu(msg, "Уведомления для арендатора ОТКЛЮЧЕНЫ")

    # Сделаем простой выход
    else:
        user.menu = "menu"
        user.extra = None
        return arendator_menu(msg)

# Когда нам пришло сообщение об окончании договора
def arendator_event_end_date(msg):
    id = str(msg["uid"])
    user = users[id]
    #dom = doma[user.doma[user.extra["name"]]]  # Дом
    txt = msg["body"]

    # Подтверждение оплаты
    if smiles.dogovor in txt:
        user.menu = "arendator_dogovor"
        return arendator_dogovor(msg)

    # Отключение уведомлений
    elif smiles.delete in txt:
        user.notifications["arendator"] = False
        user.menu = "menu"
        user.extra = None
        user.db_update()
        return arendator_menu(msg, "Уведомления для арендатора ОТКЛЮЧЕНЫ")

    # Сделаем простой выход
    else:
        user.menu = "menu"
        user.extra = None
        return arendator_menu(msg)




######################################################################################
# Раздел квартирантов

# Аргументы добавления квартиранта
arendator_add_kvartirant_args = ("name", "telephone", "email", "vk", "period", "summa", "sposob", "last_oplata", "gorod",
                                 "start_date", "end_date", "text")
# Тексты для запросов
arendator_add_kvartirant_args_text ={
    "name": "Введите ФИО квартиранта (Например Носиков Вячеслав Игоревич)",
    "telephone": "Введите телефон квартиранта (Например 89580000000)",
    "email": "Введите емейл квартиранта (Например Nosikov12@gmail.com)",
    "vk": "Введите вконтакте квартиранта (Например vk.com/nosikov12)",
    "period": "Введите периодичность оплаты цифрой, где 1 - ежемесячно, 0.5 - раз в две недели, 3 - раз в три месяца итд (Например 1)",
    "summa": "Введите сумму оплаты в рублях (Например 15000)",
    "sposob": "Введите способ оплаты наличные/карта (Например наличные)",

    "last_oplata": "Введите дату последней оплаты в формате дд.мм.гггг (Например: 21.06.2018)",
    "gorod": "Введите город заключения договора (Например Москва)",
    "start_date": "Введите дату заключения договора в формате дд.мм.гггг (Например: 21.06.2018)",
    "end_date": "Введите дату окончания договора в формате дд.мм.гггг (Например: 21.06.2018)",
    "text": "Введите любую дополнительную информацию (Например: в семье ребенок, просили не звонить после 9 вечера)"
}
# Клавиатура
arendator_add_kvartirant_keyboard = json.dumps({
            "one_time": False, "buttons": [
                [{
                    "action": {
                        "type": "text",
                        "label": smiles.next + " Пропустить шаг"
                    },
                    "color": "default"
                }],
                [{
                    "action": {
                        "type": "text",
                        "label": smiles.back + " Отменить"
                    },
                    "color": "negative"
                },

                    {
                        "action": {
                            "type": "text",
                            "label": smiles.done + " Закончить"
                        },
                        "color": "positive"
                    }
                ]]}, ensure_ascii=False)

# Добавление квартиранта
"""
def arendator_add_kvartirant(msg):
    id = str(msg["uid"])
    user = users[id]
    txt = msg["body"]
    # Если впервые здесь
    if not "dom_id" in user.extra:
        user.extra = {"dom_id": user.doma[user.extra["name"]], "name": ""}
        return {"message": arendator_add_kvartirant_args_text["name"], "keyboard": json.dumps({
            "one_time": True, "buttons": [
                [{
                    "action": {
                        "type": "text",
                        "label": "⬅ Вернуться"
                    },
                    "color": "negative"
                }]]},
            ensure_ascii=False)}
    dom = doma[user.extra["dom_id"]]

    # Нахождение текущего момента
    zis, next = arendator_add_kvartirant_args[-1], None
    for i in reversed(arendator_add_kvartirant_args):
        if i in user.extra:
            zis = i
            break
        next = i
    print(zis, next)
    ######################
    # Если конец
    if smiles.done in txt:
        dom.add_kvartirant(user.extra)
        user.extra = {"name": dom.name}
        return arendator_view_flat(msg, "Квартирант успешно добавлен")

    # Если пропускаем
    elif smiles.next in txt:
        user.extra[zis] = None
        if zis == arendator_add_kvartirant_args[-1]:
            dom.add_kvartirant(user.extra)
            user.extra = {"name": dom.name}
            return arendator_view_flat(msg, "Квартирант успешно добавлен")
        user.extra[next] = ""
        return {"message": arendator_add_kvartirant_args_text[next], "keyboard": arendator_add_kvartirant_keyboard}

    # Если емейл
    elif zis == "email":
        if len(re.findall(r"", txt)) <= 0:
            return {"message": "Неправильный формат емейл адреса!\n" + arendator_add_kvartirant_args_text[zis],
                    "keyboard": arendator_add_kvartirant_keyboard}
        user.extra[zis] = txt
        user.extra[next] = ""
        return {"message": arendator_add_kvartirant_args_text[next], "keyboard": arendator_add_kvartirant_keyboard}

    # Дата
    elif zis in ("last_oplata", "start_date", "end_date"):
        try:
            print (txt)
            user.extra[zis] = time.mktime(time.strptime(txt.lower(), "%d.%m.%Y"))
            user.extra[next] = ""
            return {"message": arendator_add_kvartirant_args_text[next], "keyboard": arendator_add_kvartirant_keyboard}
        except Exception as exp: # Если не то
            print (exp)
            return {"message": "Неправильный формат даты!\n" + arendator_add_kvartirant_args_text[zis],
                    "keyboard": arendator_add_kvartirant_keyboard}

    # Если последний
    elif zis == arendator_add_kvartirant_args[-1]:
        user.extra[zis] = txt
        dom.add_kvartirant(user.extra)
        user.extra = {"name": dom.name}
        return arendator_view_flat(msg, "Квартирант успешно добавлен")

    # Обычный текст
    else:
        user.extra[zis] = txt
        user.extra[next] = ""
        return {"message": arendator_add_kvartirant_args_text[next], "keyboard": arendator_add_kvartirant_keyboard}
"""

# Измененение квартиранта
def arendator_add_kvartirant(msg, new=True):
    id = str(msg["uid"])
    user = users[id]
    txt = msg["body"]
    # Если впервые здесь
    if not "dom_id" in user.extra:
        user.extra = {"dom_id": user.doma[user.extra["name"]], "name": ""}
        dom = doma[user.extra["dom_id"]]
        text = arendator_add_kvartirant_args_text["name"]

        # Это чтобы если новое не вылащила кнопка удалить
        if not new:
            text += "\n(Предыдущее значение %s)" % dom.kvartirant.name
            keyb = json.dumps({
            "one_time": True, "buttons": [
                [{
                    "action": {
                        "type": "text",
                        "label": "⬅ Вернуться"
                    },
                    "color": "default"
                },
                {
                    "action": {
                        "type": "text",
                        "label": smiles.next + " Пропустить шаг"
                    },
                    "color": "default"
                }],
                [{
                    "action": {
                        "type": "text",
                        "label": smiles.delete + " Удалить квартиранта"
                    },
                    "color": "negative"
                }]
                    ]},
            ensure_ascii=False)
        else:
            keyb = json.dumps({
            "one_time": True, "buttons": [
                [{
                    "action": {
                        "type": "text",
                        "label": "⬅ Вернуться"
                    },
                    "color": "default"
                }]
                    ]},
            ensure_ascii=False)

        return {"message": text,
                "keyboard": keyb}
    dom = doma[user.extra["dom_id"]]
    kvart = dom.kvartirant

    # Нахождение текущего момента
    zis, next = arendator_add_kvartirant_args[-1], None
    for i in reversed(arendator_add_kvartirant_args):
        if i in user.extra:
            zis = i
            break
        next = i
    print(zis, next)
    ######################
    # Если конец
    if smiles.done in txt:
        if new:
            dom.add_kvartirant(user.extra)
        else:
            dom.kvart_change(user.extra)
            dom.db_update()
        user.menu = "menu"
        user.extra = {"name": dom.name}
        return arendator_view_flat(msg, "Квартирант успешно добавлен")

    # Если удаляем
    elif smiles.delete in txt and not new:
        # Если уже пробуем
        if "confirm" in user.extra:
            dom.del_kvartirant()
            user.menu = "menu"
            user.extra = {"name": dom.name}
            return arendator_view_flat(msg, "Квартирант успешно удален")
        else:
            user.extra["confirm"] = False
            return  {"message": "Вы уверены что ХОТИТЕ УДАЛИТЬ квартиранта?! Это действие невозможно отменить!",
             "keyboard": json.dumps({
                 "one_time": True, "buttons": [
                     [{
                         "action": {
                             "type": "text",
                             "label": smiles.back + " Вернуться"
                         },
                         "color": "default"
                     },
                         {
                         "action": {
                             "type": "text",
                             "label": smiles.delete + " УДАЛИТЬ"
                         },
                         "color": "negative"
                     }]
                 ]},
                 ensure_ascii=False)}

    # Попунктно (все таки возьмем работоспособностью а не лакончиностью...)
    elif zis == "name":
        if smiles.next in txt:
            user.extra[zis] = None  # Если пропуск
        else:
            user.extra[zis] = txt
        user.extra[next] = ""
        text = arendator_add_kvartirant_args_text[next]
        if not new:
            text += "\n(Предыдущее значение: %s)" % kvart.contacts["telephone"]
        return {"message": text, "keyboard": arendator_add_kvartirant_keyboard}

    elif zis == "telephone":
        if smiles.next in txt:
            user.extra[zis] = None  # Если пропуск
        else:
            user.extra[zis] = txt
        user.extra[next] = ""
        text = arendator_add_kvartirant_args_text[next]
        if not new:
            text+= "\n(Предыдущее значение: %s)" % kvart.contacts["email"]
        return {"message": text, "keyboard": arendator_add_kvartirant_keyboard}

    elif zis == "email":
        # Проверка на емейл
        if smiles.next in txt:
            user.extra[zis] = None  # Если пропуск
        else:
            if len(re.findall(r"", txt)) <= 0: #TODO
                return {"message": "Неправильный формат емейл адреса!\n" + arendator_add_kvartirant_args_text[zis],
                        "keyboard": arendator_add_kvartirant_keyboard}
            user.extra[zis] = txt
        user.extra[next] = ""
        text = arendator_add_kvartirant_args_text[next]
        if not new:
            text += "\n(Предыдущее значение: %s)" % kvart.contacts["vk"]
        return {"message": text, "keyboard": arendator_add_kvartirant_keyboard}

    elif zis == "vk":
        # Проверка на емейл
        if smiles.next in txt:
            user.extra[zis] = None  # Если пропуск
        else:
            try:
                domain = txt[txt.rfind("/") + 1:]
                ret = botvk.api().users.get(user_ids=domain)
                d = "vk.com/id"+str(ret[0]["uid"])
            except:
                return {"message": "Недействительная ссылка!\n" + arendator_add_kvartirant_args_text[zis],
                        "keyboard": arendator_add_kvartirant_keyboard}

            user.extra[zis] = d
        user.extra[next] = ""
        text = arendator_add_kvartirant_args_text[next]
        if not new:
            text += "\n(Предыдущее значение: %s)" % kvart.oplata["period"]
        return {"message": text, "keyboard": arendator_add_kvartirant_keyboard}

    elif zis == "period":
        if smiles.next in txt:
            user.extra[zis] = None  # Если пропуск
        else:
            user.extra[zis] = txt
        user.extra[next] = ""
        text = arendator_add_kvartirant_args_text[next]
        if not new:
            text += "\n(Предыдущее значение: %s)" % kvart.oplata["summa"]
        return {"message": text, "keyboard": arendator_add_kvartirant_keyboard}

    elif zis == "summa":
        if smiles.next in txt:
            user.extra[zis] = None  # Если пропуск
        else:
            user.extra[zis] = txt
        user.extra[next] = ""
        text = arendator_add_kvartirant_args_text[next]
        if not new:
            text += "\n(Предыдущее значение: %s)" % kvart.oplata["sposob"]
        return {"message": text, "keyboard": arendator_add_kvartirant_keyboard}

    elif zis == "sposob":
        if smiles.next in txt:
            user.extra[zis] = None  # Если пропуск
        else:
            user.extra[zis] = txt
        user.extra[next] = ""

        text = arendator_add_kvartirant_args_text[next]
        if not new:
            if kvart.last_oplata:
                #tm = time.strftime("%d %m %Y", time.gmtime(kvart.last_oplata))
                tm = str(kvart.last_oplata.date())
            else:
                tm = "не указано"
            text += "\n(Предыдущее значение: %s)" % tm

        return {"message": text, "keyboard": arendator_add_kvartirant_keyboard}

    elif zis == "last_oplata":
        if smiles.next in txt:
            user.extra[zis] = None  # Если пропуск
        else:
            try:
                print("Пробуем распарсить дату", txt)
                #user.extra[zis] = time.mktime(time.strptime(txt.lower(), "%d.%m.%Y"))
                user.extra[zis] = datetime.datetime.strptime(txt.lower(), "%d.%m.%Y")

            except Exception as exp:  # Если не то
                print(exp)
                return {"message": "Неправильный формат даты!\n" + arendator_add_kvartirant_args_text[zis],
                        "keyboard": arendator_add_kvartirant_keyboard}
        user.extra[next] = ""
        text = arendator_add_kvartirant_args_text[next]
        if not new:
            text += "\n(Предыдущее значение: %s)" % kvart.dogovor["gorod"]
        return {"message": text, "keyboard": arendator_add_kvartirant_keyboard}

    elif zis == "gorod":
        if smiles.next in txt:
            user.extra[zis] = None  # Если пропуск
        else:
            user.extra[zis] = txt
        user.extra[next] = ""

        text = arendator_add_kvartirant_args_text[next]
        if not new:
            if kvart.dogovor["start_date"]:
                tm = str(kvart.dogovor["start_date"].date())
                #tm = time.strftime("%d %m %Y", time.gmtime(kvart.last_oplata))
            else:
                tm = "не указано"
            text += "\n(Предыдущее значение: %s)" % tm
        return {"message": text, "keyboard": arendator_add_kvartirant_keyboard}

    elif zis == "start_date":
        if smiles.next in txt:
            user.extra[zis] = None  # Если пропуск
        else:
            try:
                print("Пробуем распарсить дату", txt)
                #user.extra[zis] = time.mktime(time.strptime(txt.lower(), "%d.%m.%Y"))
                user.extra[zis] = datetime.datetime.strptime(txt.lower(), "%d.%m.%Y")
            except Exception as exp:  # Если не то
                print(exp)
                return {"message": "Неправильный формат даты!\n" + arendator_add_kvartirant_args_text[zis],
                        "keyboard": arendator_add_kvartirant_keyboard}
        user.extra[next] = ""

        text = arendator_add_kvartirant_args_text[next]
        if not new:
            if kvart.dogovor["end_date"]:
                #tm = time.strftime("%d %m %Y", time.gmtime(kvart.last_oplata))
                tm = str(kvart.dogovor["end_date"].date())
            else:
                tm = "не указано"
            text += "\n(Предыдущее значение: %s)" % tm
        return {"message": text, "keyboard": arendator_add_kvartirant_keyboard}

    elif zis == "end_date":
        if smiles.next in txt:
            user.extra[zis] = None  # Если пропуск
        else:
            try:
                print("Пробуем распарсить дату", txt)
                #user.extra[zis] = time.mktime(time.strptime(txt.lower(), "%d.%m.%Y"))
                user.extra[zis] = datetime.datetime.strptime(txt.lower(), "%d.%m.%Y")
            except Exception as exp:  # Если не то
                print(exp)
                return {"message": "Неправильный формат даты!\n" + arendator_add_kvartirant_args_text[zis],
                        "keyboard": arendator_add_kvartirant_keyboard}
        user.extra[next] = ""
        text = arendator_add_kvartirant_args_text[next]
        if not new:
            text += "\n(Предыдущее значение: %s)" % kvart.text
        return {"message": text, "keyboard": arendator_add_kvartirant_keyboard}

    elif zis == "text":
        if smiles.next in txt:
            user.extra[zis] = None  # Если пропуск
        else:
            user.extra[zis] = txt

        if new:
            dom.add_kvartirant(user.extra)
        else:
            dom.kvart_change(user.extra, user.hostid)
        user.extra = {"name": dom.name}
        user.menu = "menu"
        return arendator_view_flat(msg, "Квартирант успешно добавлен")

    else:
        return arendator_view_flat(msg, "Ошибка! Возврат...")




########################################################################################################################
####        Часть клиента
########################################################################################################################
# Аналогично коду сверху значения
client_add_kvartirant_args = ("name", "telephone", "email", "vk", "period", "summa", "sposob", "last_oplata", "gorod",
                                 "start_date", "end_date", "text")
# И текста для них
client_add_kvartirant_args_text ={
    "name": "Введите ФИО хозяина квартиры (Например Носиков Вячеслав Игоревич)",
    "telephone": "Введите телефон хозяина квартиры (Например 89580000000)",
    "email": "Введите емейл хозяина квартиры (Например Nosikov12@gmail.com)",
    "vk": "Введите вконтакте хозяина квартиры (Например vk.com/nosikov12)",
    "period": "Введите периодичность оплаты цифрой, где 1 - ежемесячно, 0.5 - раз в две недели, 3 - раз в три месяца итд (Например 1)",
    "summa": "Введите сумму оплаты в рублях (Например 15000)",
    "sposob": "Введите способ оплаты наличные/карта (Например наличные)",

    "last_oplata": "Введите дату последней оплаты в формате дд.мм.гггг (Например: 21.06.2018)",
    "gorod": "Введите город заключения договора (Например Москва)",
    "start_date": "Введите дату заключения договора в формате дд.мм.гггг (Например: 21.06.2018)",
    "end_date": "Введите дату окончания договора в формате дд.мм.гггг (Например: 21.06.2018)",
    "text": "Введите любую дополнительную информацию (Например: в семье ребенок, просили не звонить после 9 вечера)"
}

# Добавление и изменение квартиры
def client_add_kvartira(msg, new=True):
    id = str(msg["uid"])
    user = users[id]
    txt = msg["body"]

    if (not user.extra) or (not "name" in user.extra):
        user.extra = {"name": ""}
        text = client_add_kvartirant_args_text["name"]
        if not new:
            text += "\n(Предыдущее значение: %s)" % user.kvartiri.name
        return {"message": text, "keyboard": arendator_add_kvartirant_keyboard}
    kvart = user.kvartiri

    # Нахождение текущего момента
    zis, next = client_add_kvartirant_args[-1], None
    for i in reversed(client_add_kvartirant_args):
        if i in user.extra:
            zis = i
            break
        next = i
    print(zis, next)
    ######################
    # Если конец
    if smiles.done in txt:
        if new:
            user.add_kvartiri()
        else:
            user.kvart_change()
        user.menu = "menu"
        user.extra = None
        return client_menu(msg, "Квартирант успешно добавлен")
    # Если удаляем
    elif smiles.delete in txt and not new:
        # Если уже пробуем
        if "confirm" in user.extra:
            user.del_kvartiri()
            return client_menu(msg, "Квартирант успешно удален")
        else:
            user.extra["confirm"] = False
            return {"message": "Вы уверены что ХОТИТЕ УДАЛИТЬ квартиранта?! Это действие невозможно отменить!",
                    "keyboard": json.dumps({
                        "one_time": True, "buttons": [
                            [{
                                "action": {
                                    "type": "text",
                                    "label": smiles.back + " Вернуться"
                                },
                                "color": "default"
                            },
                                {
                                "action": {
                                    "type": "text",
                                    "label": smiles.delete + " УДАЛИТЬ"
                                },
                                "color": "negative"
                            }]
                        ]},
                        ensure_ascii=False)}
    # Попунктно (все таки возьмем работоспособностью а не лакончиностью...)
    elif zis == "name":
        if smiles.next in txt:
            user.extra[zis] = None  # Если пропуск
        else:
            user.extra[zis] = txt
        user.extra[next] = ""
        text = client_add_kvartirant_args_text[next]
        if not new:
            text += "\n(Предыдущее значение: %s)" % kvart.contacts["telephone"]
        return {"message": text.replace("None", "*не указано*"), "keyboard": arendator_add_kvartirant_keyboard}

    elif zis == "telephone":
        if smiles.next in txt:
            user.extra[zis] = None  # Если пропуск
        else:
            user.extra[zis] = txt
        user.extra[next] = ""
        text = client_add_kvartirant_args_text[next]
        if not new:
            text += "\n(Предыдущее значение: %s)" % kvart.contacts["email"]
        return {"message": text.replace("None", "*не указано*"), "keyboard": arendator_add_kvartirant_keyboard}

    elif zis == "email":
        # Проверка на емейл
        if smiles.next in txt:
            user.extra[zis] = None  # Если пропуск
        else:
            if len(re.findall(r"", txt)) <= 0:  # TODO
                return {"message": "Неправильный формат емейл адреса!\n" + client_add_kvartirant_args_text[zis],
                        "keyboard": arendator_add_kvartirant_keyboard}
            user.extra[zis] = txt
        user.extra[next] = ""
        text = client_add_kvartirant_args_text[next]
        if not new:
            text += "\n(Предыдущее значение: %s)" % kvart.contacts["vk"]
        return {"message": text.replace("None", "*не указано*"), "keyboard": arendator_add_kvartirant_keyboard}

    elif zis == "vk":
        # Проверка на емейл
        if smiles.next in txt:
            user.extra[zis] = None  # Если пропуск
        else:
            try:
                domain = txt[txt.rfind("/") + 1:]
                ret = botvk.api().users.get(user_ids=domain)
                d = "vk.com/id" + str(ret[0]["uid"])
            except:
                return {"message": "Недействительная ссылка!\n" + client_add_kvartirant_args_text[zis],
                        "keyboard": arendator_add_kvartirant_keyboard}

            user.extra[zis] = d
        user.extra[next] = ""
        text = client_add_kvartirant_args_text[next]
        if not new:
            text += "\n(Предыдущее значение: %s)" % kvart.oplata["period"]
        return {"message": text.replace("None", "*не указано*"), "keyboard": arendator_add_kvartirant_keyboard}

    elif zis == "period":
        if smiles.next in txt:
            user.extra[zis] = None  # Если пропуск
        else:
            user.extra[zis] = txt
        user.extra[next] = ""
        text = client_add_kvartirant_args_text[next]
        if not new:
            text += "\n(Предыдущее значение: %s)" % kvart.oplata["summa"]
        return {"message": text.replace("None", "*не указано*"), "keyboard": arendator_add_kvartirant_keyboard}

    elif zis == "summa":
        if smiles.next in txt:
            user.extra[zis] = None  # Если пропуск
        else:
            user.extra[zis] = txt
        user.extra[next] = ""
        text = client_add_kvartirant_args_text[next]
        if not new:
            text += "\n(Предыдущее значение: %s)" % kvart.oplata["sposob"]
        return {"message": text.replace("None", "*не указано*"), "keyboard": arendator_add_kvartirant_keyboard}

    elif zis == "sposob":
        if smiles.next in txt:
            user.extra[zis] = None  # Если пропуск
        else:
            user.extra[zis] = txt
        user.extra[next] = ""

        text = client_add_kvartirant_args_text[next]
        if not new:
            if kvart.last_oplata:
                #tm = time.strftime("%d %m %Y", time.gmtime(kvart.last_oplata))
                tm = str(kvart.last_oplata.date())
            else:
                tm = "*не указано*"
            text += "\n(Предыдущее значение: %s)" % tm

        return {"message": text, "keyboard": arendator_add_kvartirant_keyboard}

    elif zis == "last_oplata":
        if smiles.next in txt:
            user.extra[zis] = None  # Если пропуск
        else:
            try:
                print("Пробуем распарсить дату", txt)
                #user.extra[zis] = time.mktime(time.strptime(txt.lower(), "%d.%m.%Y"))
                user.extra[zis] = datetime.datetime.strptime(txt.lower(), "%d.%m.%Y")
                if user.extra[zis].year < 2005 or user.extra[zis].year > 2100:
                    raise Exception()

            except Exception as exp:  # Если не то
                print(exp)
                return {"message": "Неправильный формат даты!\n" + client_add_kvartirant_args_text[zis],
                        "keyboard": arendator_add_kvartirant_keyboard}
        user.extra[next] = ""
        text = client_add_kvartirant_args_text[next]
        if not new:
            text += "\n(Предыдущее значение: %s)" % kvart.dogovor["gorod"]
        return {"message": text.replace("None", "*не указано*"), "keyboard": arendator_add_kvartirant_keyboard}

    elif zis == "gorod":
        if smiles.next in txt:
            user.extra[zis] = None  # Если пропуск
        else:
            user.extra[zis] = txt
        user.extra[next] = ""

        text = client_add_kvartirant_args_text[next]
        if not new:
            if kvart.dogovor["start_date"]:
                #tm = time.strftime("%d %m %Y", time.gmtime(kvart.last_oplata))
                tm = str(kvart.dogovor["start_date"].date())
            else:
                tm = "*не указано*"
            text += "\n(Предыдущее значение: %s)" % tm
        return {"message": text, "keyboard": arendator_add_kvartirant_keyboard}

    elif zis == "start_date":
        if smiles.next in txt:
            user.extra[zis] = None  # Если пропуск
        else:
            try:
                print("Пробуем распарсить дату", txt)
                #user.extra[zis] = time.mktime(time.strptime(txt.lower(), "%d.%m.%Y"))
                user.extra[zis] = datetime.datetime.strptime(txt.lower(), "%d.%m.%Y")
            except Exception as exp:  # Если не то
                print(exp)
                return {"message": "Неправильный формат даты!\n" + client_add_kvartirant_args_text[zis],
                        "keyboard": arendator_add_kvartirant_keyboard}
        user.extra[next] = ""

        text = client_add_kvartirant_args_text[next]
        if not new:
            if kvart.dogovor["end_date"]:
                #tm = time.strftime("%d %m %Y", time.gmtime(kvart.last_oplata))
                tm = str(kvart.dogovor["end_date"].date())
            else:
                tm = "*не указано*"
            text += "\n(Предыдущее значение: %s)" % tm
        return {"message": text, "keyboard": arendator_add_kvartirant_keyboard}

    elif zis == "end_date":
        if smiles.next in txt:
            user.extra[zis] = None  # Если пропуск
        else:
            try:
                print("Пробуем распарсить дату", txt)
                #user.extra[zis] = time.mktime(time.strptime(txt.lower(), "%d.%m.%Y"))
                user.extra[zis] = datetime.datetime.strptime(txt.lower(), "%d.%m.%Y")
            except Exception as exp:  # Если не то
                print(exp)
                return {"message": "Неправильный формат даты!\n" + client_add_kvartirant_args_text[zis],
                        "keyboard": arendator_add_kvartirant_keyboard}
        user.extra[next] = ""
        text = client_add_kvartirant_args_text[next]
        if not new:
            text += "\n(Предыдущее значение: %s)" % kvart.text
        return {"message": text.replace("None", "*не указано*"), "keyboard": arendator_add_kvartirant_keyboard}

    elif zis == "text":
        if smiles.next in txt:
            user.extra[zis] = None  # Если пропуск
        else:
            user.extra[zis] = txt

        # Т.к это уже конец
        if new:
            user.add_kvartiri()
        else:
            kvart.change(user.extra, user.host, user.id, False)
        return client_menu(msg, "Квартирант успешно добавлен")

    else:
        return client_menu(msg, "Ошибка! Возврат...")

# Удаление квартиры
def client_delete_kvartira(msg):
    id = str(msg["uid"])
    user = users[id]
    txt = msg["body"]

    if user.extra and smiles.delete in txt:
        user.del_kvartiri()
        return client_menu(msg, "Квартира успешно удалена.")

    else:
        user.extra = {"confirm":False}
        return {"message": "Вы уверены что хотите УДАЛИТЬ КВАРТИРУ?\nЭто действие нельзя отменить", "keyboard":
            json.dumps({ "one_time": False, "buttons": [
                [{
                    "action": {
                        "type": "text",
                        "label": smiles.back + " Назад"
                    },
                    "color": "default"
                },
                    {
                    "action": {
                        "type": "text",
                        "label": smiles.delete + " УДАЛИТЬ"
                    },
                    "color": "negative"
                }
                ]]}, ensure_ascii=False)}

# Импорт
def client_copy_kvartira(msg):
    id = str(msg["uid"])
    user = users[id]

    # TODO
    user.menu = "menu"
    return (client_menu(msg, "Раздел в разработке"))

# Настройка уведомлений
def client_edit_notifications(msg):
    id = str(msg["uid"])
    user = users[id]
    txt = msg["body"]

    # Текущее значение
    nots = user.notifications[user.type]

    if smiles.done in txt:
        user.notifications[user.type] = True
        user.menu = "menu"
        user.db_update()
        return client_menu(msg, "Уведомления для съемщика ВКЛЮЧЕНЫ")

    elif smiles.delete in txt:
        user.notifications[user.type] = False
        user.menu = "menu"
        user.db_update()
        return client_menu(msg, "Уведомления для съемщика ВЫКЛЮЧЕНЫ")

    # Иначе выводим запрос
    txt = "Сейчас уведомления для съемщика: *%s*" % ("ВКЛЮЧЕНЫ" if nots else "ВЫКЛЮЧЕНЫ")

    keyb = json.dumps({
        "one_time": False, "buttons": [
            [{
                "action": {
                    "type": "text",
                    "label": smiles.delete + " Выключить"
                },
                "color": "negative"
            },
                {
                    "action": {
                        "type": "text",
                        "label": smiles.done + " Включить"
                    },
                    "color": "positive"
                }],
            [{
                "action": {
                    "type": "text",
                    "label": smiles.back + " Отменить"
                },
                "color": "default"
            }
            ]]}, ensure_ascii=False)

    return {"message": txt, "keyboard": keyb}

# Настройка оплаты
def client_edit_money(msg):
    id = str(msg["uid"])
    user = users[id]

    #TODO
    user.menu = "menu"
    return (client_menu(msg, "Раздел в разработке"))

# Продление договора
def client_dogovor(msg):
    id = str(msg["uid"])
    user = users[id]

    # TODO
    user.menu = "menu"
    return client_menu(msg, "Функция в разработке")


# ИВЕНТЫ!
# Когда нам пишло сообщение об оплате
def client_event_oplata(msg):
    id = str(msg["uid"])
    user = users[id]
    txt = msg["body"]

    # Подтверждение оплаты
    if smiles.checked in txt:
        user.confirm_oplata()
        user.menu = "menu"
        user.extra = None
        return client_menu(msg, "Оплата подтверждена")
    # Отключение уведомлений
    elif smiles.delete in txt:
        user.notifications["client"] = False
        user.menu = "menu"
        user.extra = None
        user.db_update()
        return client_menu(msg, "Уведомления для съемщика ОТКЛЮЧЕНЫ")

    # Сделаем простой выход
    else:
        user.menu = "menu"
        user.extra = None
        return client_menu(msg)

# Когда нам пришло сообщение об окончании договора
def client_event_end_date(msg):
    id = str(msg["uid"])
    user = users[id]
    txt = msg["body"]

    # Подтверждение оплаты
    if smiles.dogovor in txt:
        user.menu = "arendator_dogovor"
        return client_dogovor(msg)

    # Отключение уведомлений
    elif smiles.delete in txt:
        user.notifications["client"] = False
        user.db_update()
        user.menu = "menu"
        user.extra = None
        return client_menu(msg, "Уведомления для съемщика ОТКЛЮЧЕНЫ")

    # Сделаем простой выход
    else:
        user.menu = "menu"
        user.extra = None
        return client_menu(msg)

