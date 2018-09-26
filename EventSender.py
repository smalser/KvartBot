import time, datetime

from vkontakte import botvk
import DataBase as db
from smiles import smiles

# Тащим варики
users = db.DB_users
doma = db.DB_doma

# Создадим словарь ответов
api = {
    "vk": botvk
}

# Время как част опроверяем
CHECK_TIME = 60*60*3 #3 часа    # Время через которое проверяется событие
# Количество дней когда мы просим заплатить
TIMERS_OPLATA = (-10, -5, -1, 0, 5)
TIMERS_END_DATE = (-15, -5, -1, 0, 5)

########################################################################################################################
#       Чекер событий
########################################################################################################################
class EventSender:
    def __init__(self):
        self.last_check = 0
        self.index = []

    # Переведем время из таблицы в секунды
    def tosecs(self):
        pass

    # Перевод итема в словарь
    def todict(self, item):
        d = {}
        for i, it in enumerate(db.DB_EVENTS_SLOTS):
            d[it] = item[i]

        # делаем ид строкой(так уж надо)
        d["N"] = d["N"]

        return d

    def check(self):
        # Если пора смотреть
        if time.time() > self.last_check + CHECK_TIME:
            co, cu = db.connect()
            txt = "SELECT * FROM %s ORDER BY time LIMIT 10" % db.EVENTS_TABLE
            cu.execute(txt)
            r = cu.fetchall()
            co.close()
            # Если нет то выходим и забываем но пол суток
            if not r:
                self.last_check = time.time()
                return

            # Вбиваем в индекс новые значения
            self.index = [self.todict(x) for x in r]
            # Проверяем пора ли выполнять
            print("Запланированные события:")
            for i in self.index:
                print(" ", i)
                if i["time"] < datetime.datetime.now().date():
                    print("   Нужно!")
                    self.do(i)
                    return # Выходим и вернемся в следующем цикле

            self.last_check = time.time()

    # Выпленение действия
    def do(self, event):
        user = users.get(event["host"],event["id"])
        if event["dom"]:
            # Если в доме
            dom = doma[event["dom"]]
            kvart = dom.kvartirant
        else:
            # Если в пользователе
            kvart = user.kvartiri

        # Проверка валидности
        if kvart.isvalid(event):
            if event["dom"]: # Арендатор
                self.send_arendator(event, user, dom, kvart)
            else:            # Клиент
                self.send_client(event, user, kvart)

        else:
            print("Событие не валидно", str(event), str(kvart.event))
            kvart.db_event_update(event["host"],event["id"], event["dom"])

    # Функция выполнения
    def send_arendator(self, event, user, dom, kvart):
        print("Выполняем что то")
        if event["message"] == "oplata":
            send_arendator_oplata(event, user, dom, kvart)
        elif event["message"] == "end_date":
            send_arendator_end_date(event, user, dom, kvart)
        else:
            print("ВЫход за рамки...")
        pass

    # Функция выполнения
    def send_client(self, event, user, kvart):
        print("Выполняем что то")
        if event["message"] == "oplata":
            send_client_oplata(event, user, kvart)
        elif event["message"] == "end_date":
            send_client_end_date(event, user, kvart)
        else:
            print("ВЫход за рамки...")

event_sender = EventSender()

########################################################################################################################
send_client_oplata_text_perfect ="""
Здравствуйте. 
 Это сервис Квартирбил напоминает вам, что до оплаты квартиры (имя квартиры )осталось N дня(ей).   
Вы должны оплатить (абонентская плата) рублей(я) до ( дата оплаты). Оплата ( наличными, безналично, на карту, пайпел, яндекс-деньги, вебмани, биткойн. ) ( если не налично - реквизиты для оплаты. А потом и партнерская ссылка)

Напоминаем, что ваш арендатель  (фио арендодателя), связаться с ним можно по телефону ( телефон) ,послать электронное письмо на адрес ( mail) или написать приватное сообщение в VK - ( ссылка на профиль).

Если вы оплатите заранее, можете проставить оплату в нашем сервисе, что бы мы лишний раз вас не беспокоили. Делается это после выбора квартиры в разделе оплата. Если вам больше не нужны наши напоминания вы всегда можете отключить в личном кабинете.

"""
send_client_oplata_text ="""
Здравствуйте. 
Это сервис Квартирбил напоминает вам, что до оплаты квартиры осталось '{dt}' дня(ей).   
Вы должны оплатить '{summa}' рублей(я) до '{payday}'. Способ оплаты: '{oplata}' 

Если вы оплатите заранее, можете проставить оплату в нашем сервисе, что бы мы лишний раз вас не беспокоили. Делается это после выбора квартиры в разделе оплата. 
Если вам больше не нужны наши напоминания вы всегда можете отключить в личном кабинете.
Ваш Квартирбил.
"""
# Напоминание клиенту что пора платить
def send_client_oplata(event, user, kvart):
    host = event["host"]
    id = event["id"]
    number = kvart.event["oplata"][2] # Количество дней

    # Дней до оплаты
    payday = kvart.last_oplata + datetime.timedelta(days=number)
    # Сообщение
    txt = send_client_oplata_text.format(dt=number, summa=kvart.oplata["summa"], payday=payday.date(),
                                         oplata=kvart.oplata["sposob"]).replace("None", "*не указано*")

    # Шлем сообщение
    api[host].send_message(id, dict(message=txt))
    #user.menu = ""
    #TODO Создать меню типа после сообщения
    # И хачим хранилище
    kvart.db_delete_event(event["N"])
    kvart.event["oplata"] = None
    kvart.db_create_event_oplata(host, id, number = number)

    user.db_update()
    print("Уведомление отправлено и обновлено")


#########################################################
send_client_end_date_text_perfect = """
Здравствуйте. Это сервис Квартирбил напоминает вам, что подходит к концу договор о аренде квартиры (имя квартиры). Если вы собираетесь дальше проживать в этой квартире, то предлагаем вам сверить данные, распечатать и подписать договор с хозяином квартиры.
Для этого в боте выберите квартиру (имя квартиры)  и меню ( договор на новый срок) . Дальше действуйте по подсказке бота.
Если вам больше не нужны наши напоминания вы всегда можете отключить в личном кабинете.
"""
send_client_end_date_text = """
Здравствуйте.
Это сервис Квартирбил напоминает вам, что через '{dt}' дня(ей) подходит к концу договор о аренде квартиры. Если вы собираетесь дальше проживать в этой квартире, то предлагаем вам сверить данные, распечатать и подписать договор с хозяином квартиры.
Если вам больше не нужны наши напоминания вы всегда можете отключить в личном кабинете.
Ваш Квартирбил.
"""
# Напоминание клиенту о том что кончается договор
def send_client_end_date(event, user, kvart):
    host = event["host"]
    id = event["id"]
    number = kvart.event["oplata"][2]

    # Сообщение
    txt = send_client_end_date_text.format(dt=number)

    # Шлем сообщение
    api[host].send_message(id, dict(message=txt))
    # user.menu = ""
    # TODO Создать меню типа после сообщения
    # И хачим хранилище
    kvart.db_delete_event(event["N"])
    kvart.event["end_date"] = None
    kvart.db_create_event_end_date(host, id, number=number)

    user.db_update()
    print("Уведомление отправлено и обновлено")


########################################################################################################################
send_arendator_oplata_text_perfect = """
Здравствуйте  
Это сервис Квартирбил напоминает вам, что ваш жилец (фио жильца) должен заплатить за проживание в  квартире (имя квартиры)  до ( дата платежа) сумму (сумма)
Вы выбрали способ оплаты ( наличными, безналично, на карту, пайпел, яндекс-деньги, вебмани, биткойн )
Связаться  с жильцом для приема оплаты ( фио жильца) можно по следующим контактам ( телефон, мыл, профиль соцсети) 
"""
send_arendator_oplata_text = """
Здравствуйте.
Это сервис Квартирбил напоминает вам, что ваш жилец '{FIO}' должен заплатить за проживание в квартире '{dom_name}' до '{payday}' сумму '{summa}'
Вы выбрали способ оплаты '{oplata_type}'
{contacts}
"""
# Напоминание арендатору что пора собирать дань
def send_arendator_oplata(event, user, dom, kvart):
    host = event["host"]
    id = event["id"]
    number = kvart.event["oplata"][2]

    # Дней до оплаты
    payday = kvart.last_oplata + datetime.timedelta(days=number)

    # Добавление контактов
    contacts = "*не указано*"
    if any(kvart.contacts[i] for i in kvart.contacts):
        contacts = "Связаться с жильцом для приема оплаты можно по следующим контактам:\n"
        if kvart.contacts["telephone"]:
            contacts += "Телефон: " + kvart.contacts["telephone"] + "\n"
        if kvart.contacts["email"]:
            contacts += "Емейл: " + kvart.contacts["email"] + "\n"
        if kvart.contacts["vk"]:
            vk = kvart.contacts["vk"].split("/")[-1]
            contacts += "*%s (Вконтакте)" % vk

    txt = send_arendator_oplata_text.format(FIO=kvart.name, dom_name=dom.name, payday=payday.date(), summa=kvart.oplata["summa"],
                                         oplata_type=kvart.oplata["sposob"], contacts=contacts).replace("None", "*не указано*")

    # Шлем сообщение
    api[host].send_message(id, dict(message=txt))
    # user.menu = ""
    # TODO Создать меню типа после сообщения
    # И хачим хранилище
    kvart.db_delete_event(event["N"])
    kvart.event["oplata"] = None
    kvart.db_create_event_oplata(host, id, dom=dom.id, number=number)

    dom.db_update()
    print("Уведомление отправлено и обновлено")


######################################################
send_arendator_end_date_text_perfect = """
Здравствуйте. Это сервисе Квартирбил напоминает вам, что подходит к концу договор о аренде квартир( имя квартиры). Если вы собираетесь дальше сдавать квартиру жильцу (ФИО Жильца) , то предлагаем вам сверить данные, распечатать и подписать договор с жильцом.
Для этого в боте выберите квартиру (имя квартиры)  и меню ( договор на новый срок) . Дальше действуйте по подсказке бота.
Если вам больше не нужны наши напоминания вы всегда можете отключить в личном кабинете.
"""
send_arendator_end_date_text = """
Здравствуйте.
Это сервисе Квартирбил напоминает вам, что подходит к концу договор о аренде квартиры '{kvart_name}'.
Если вы собираетесь дальше сдавать квартиру жильцу '{name}', то предлагаем вам сверить данные, распечатать и подписать договор с жильцом.
Если вам больше не нужны наши напоминания вы всегда можете отключить в личном кабинете.
"""
# Арендатору об окончании договора
def send_arendator_end_date(event, user, dom, kvart):
    host = event["host"]
    id = event["id"]
    number = kvart.event["oplata"][2]

    txt = send_arendator_end_date_text.format(kvart_name=dom.name, name=kvart.name)

    # Шлем сообщение
    api[host].send_message(id, dict(message=txt))
    # user.menu = ""
    # TODO Создать меню типа после сообщения
    # И хачим хранилище
    kvart.db_delete_event(event["N"])
    kvart.event["end_date"] = None
    kvart.db_create_event_end_date(host, id, dom=dom.id, number=number)
    dom.db_update()
    print("Уведомление отправлено и обновлено")








