import time, datetime, json, copy
import mysql.connector as sql

from smiles import smiles

# Структура базы данных
DATABASE = "test"       # Название БД
USER_TABLE = "users"        # Таблица в БД
DOMA_TABLE = "doma"         # Таблица в бд
EVENTS_TABLE = "events"     # События(напомнить об оплате итд)
# Название колонок в бд1
DB_USER_SLOTS = ("hostid", "host","id", "type", "menu", "extra", "add_time", "doma", "kvartiri", "notifications")
# Название колонок в бд2
DB_DOMA_SLOTS = ("id", "name", "owner_hostid", "add_time", "adress", "square", "rooms", "sanuzel", "extras", "text", "photos", "kvartirant")
#
DB_EVENTS_SLOTS = ("N", "time", "host", "id", "message", "dom")
# Создание таблиц
_db_users_Create = """CREATE TABLE users (hostid varchar(20) not NULL, host varchar(2), id varchar(10), type varchar(10), menu varchar(20), extra text, add_time datetime, doma text, kvartiri text, notifications BOOLEAN NOT NULL DEFAULT TRUE, primary key (hostid)); CREATE INDEX hostid ON users(hostid)"""
_db_doma_Create = """CREATE TABLE doma (id INT UNSIGNED NOT NULL AUTO_INCREMENT, name varchar(30), owner_hostid varchar(20), add_time datetime, adress text, square varchar(10), rooms varchar(10), sanuzel varchar(10), extras text, text text, photos text, kvartirant text, PRIMARY KEY(id)); CREATE INDEX id ON doma(id)"""
_db_events_Create = """CREATE TABLE events (N INT UNSIGNED NOT NULL AUTO_INCREMENT, time date, host VARCHAR(2), id VARCHAR(10), message varchar(15), dom varchar(10), primary key(N)); CREATE INDEX time ON events(time);"""

# Функция для подключения к ДБ
def connect():
    connection = sql.connect(host="localhost", user="root", password="root", db=DATABASE)
    cursor = connection.cursor()
    return connection, cursor
########################################################################################################################
def time_to_datetime(tm):       # дататайм в время для БД
    if not tm:
        return tm
    return tm.strftime('%Y-%m-%d %H:%M:%S')
def datetime_to_time(tm):       # Время из бд в даттайм
    # Если нет
    if not tm:
        return tm
    # Если это уже даттайм
    if type(tm) == datetime.datetime:
        return tm
    return datetime.datetime.strptime(tm, '%Y-%m-%d %H:%M:%S')
def time_to_date(tm):           # Из даттайм в дату
    if not tm:
        return "None"
    return tm.strftime('%d.%m.%Y')
def time_to_DBdate(tm):
    if not tm:
        return None
    else:
        return tm.strftime('%Y-%m-%d')
########################################################################################################################
#  Фикс джсона
def json_def(obj):
    if type(obj) == datetime:
        return str(obj)
    else:
        return json._default_encoder(obj)

########################################################################################################################
# Класс пользователя
class User:
    # Инитуем дефолты
    def __init__(self):
        # Основные
        self.id = None
        self.host = None
        self.hostid = None
        self.add_time = None

        # доп значения
        self.type = None
        self.menu = None
        self.extra = None

        # общие значения рабочие
        self.notifications = True

        # Для Аренд
        self.doma = None

        # Для клиента
        self.kvartiri = None

    # Типа статического инициализатора, котоырй мы полюбим
    @staticmethod
    def Create(id, host):
        self = User()               # Создаем
        self.id = id                # ид
        self.host = host            # Откуда (вк/тг/вб)
        self.hostid = "%s_%s" % (host, id) # Для базы данных
        self.add_time = datetime.datetime.now()  # Время добавления (хз зачем, но я так хочу)

        self.menu = ""              # Меню
        self.extra = None           # Экстра параметры

        self.db_add()               # Загружаем его в ДБ
        return self                 # Возвращаем объект

    # Это метод загрузки объекта из ДБ(статик)
    @staticmethod
    def db_load(id, host):
        # Загружаем из ДБ
        response = """SELECT * FROM {0} WHERE (hostid = "{1}_{2}")""".format(USER_TABLE, host, id)
        co, cu = connect()
        cu.execute(response)
        zis = cu.fetchall()[0]
        zis = {DB_USER_SLOTS[i]: str(k) for i,k in enumerate(zis)}
        print (zis)
        co.close()

        # Выбираем тип
        if zis["type"] == "client":
            self = Client()
        elif zis["type"] == "arendator":
            self = Arendator()
        else:
            self = User()

        # Заполняем поля
        for i in zis:
            if not zis[i]:
                continue
            elif zis[i] == "None":
                continue
            elif i == "add_time":
                self.__dict__[i] = datetime_to_time(zis[i])
            elif i == "kvartiri":
                self.__dict__[i] = Kvartirant.load(json.loads(zis[i]))
            elif zis[i].strip().startswith("{") and zis[i].strip().endswith("}"):
                self.__dict__[i] = json.loads(zis[i])
            elif zis[i].strip().startswith("[") and zis[i].strip().endswith("]"):
                self.__dict__[i] = json.loads(zis[i])
            else:
                self.__dict__[i] = zis[i]

        return self # Возвращаем

    # Добавление нового в БД
    def db_add(self):
        # Распределяем переменыне на поля
        vars = {}
        for i in self.__dict__:
            obj = self.__dict__[i]
            if obj:
                # Если это дикт - превращаем в жсон
                if type(obj) == dict or type(obj) == list:
                    vars[i] = ("'" + json.dumps(obj,ensure_ascii=False) + "'")
                # Если квартирант
                elif type(obj) == Kvartirant:
                    vars[i] = ("'" + obj.drop() + "'")
                # Если время - в другое время(???)
                elif i == "add_time":
                    vars[i] = "'" +str(time_to_datetime(obj)) + "'"
                # Иниче просто ставим строку
                else:
                    vars[i] = "'" + str(obj) + "'"
        responce = '''INSERT INTO {0} ({1}) VALUES ({2})'''.format(USER_TABLE,
                                                                   ",".join(vars.keys()), ",".join(vars.values()))
        print (responce)
        co, cu = connect()
        cu.execute(responce)
        co.commit()
        co.close()
        DB_users.add(self)
        print ("Пользователь %s добавлен в ДБ!" % self.hostid)

    # Обновление пользователя в базе
    def db_update(self):
        # Также делаем вары и вносим используя последовательность ключей
        vars = []
        for i in self.__dict__:
            obj = self.__dict__[i]
            if obj:
                if type(obj) == dict or type(obj) == list:
                    vars.append(i + "='" + json.dumps(obj,ensure_ascii=False) + "'")
                elif type(obj) == Kvartirant:
                    vars.append(i + "='" + obj.drop() + "'")
                elif i == "add_time":
                    vars.append(i + "='" + str(time_to_datetime(obj)) + "'")
                else:
                    vars.append(i + "='" + str(obj) + "'")
            else:
                vars.append("%s = NULL" % i)
        responce = '''UPDATE {0} SET {1} WHERE hostid = "{2}_{3}" '''.format(USER_TABLE,
                                                                                          ",".join(vars)
                                                                                          , self.host, self.id)
        print(responce)
        co, cu = connect()
        cu.execute(responce)
        co.commit()
        co.close()
        print("Пользователь %s обновлен!" % self.hostid)


# Класс клиента(Кто снимает квартиры)
class Client(User):
    def __init__(self):
        super().__init__()

    # Аналагичное создание
    @staticmethod
    def Create(id, host):
        self = Client()
        self.id = id
        self.host = host
        self.hostid = "%s_%s" % (host, id)  # Для базы данных

        self.type = "client"        # Типа - клиент
        self.menu = "menu"          # Меню делаем стандартным
        self.extra = None           # Экстры пустые
    ##########################################################

        self.kvartiri = None

    ##########################################################
        self.db_add()               # Добавим в базу
        return self

    # Добавление квартиры
    def add_kvartiri(self):
        self.kvartiri = Kvartirant.Create(self.extra, self.host, self.id)
        self.menu = "menu"
        self.extra = None

        self.db_update()

    # Удаление квартиры
    def del_kvartiri(self):
        self.kvartiri.delete()
        self.kvartiri = None
        self.menu = "menu"
        self.extra = None

        self.db_update()

    # Изменение
    def kvart_change(self, *args):
        self.kvartiri.change(self.extra, self.host, self.id)
        self.menu = "menu"
        self.extra = None
        self.db_update()

    # Подтверждение оплаты
    def confirm_oplata(self):
        if self.kvartiri:
            self.kvartiri.last_oplata = datetime.datetime.now()
            self.kvartiri.db_event_update(self.host, self.id)
            self.db_update()
            return True
        else:
            return False


# Класс арендатора(Кто сдает квартиры)
class Arendator(User):
    def __init__(self):
        super().__init__()
        self.doma = {}

    # Оверрайтим
    @staticmethod
    def Create(id, host):
        self = Arendator()
        self.id = id
        self.host = host
        self.hostid = "%s_%s" % (host, id)  # Для базы данных
        self.add_time = datetime.datetime.now()

        self.type = "arendator"
        self.menu = "menu"
        self.extra = None
    ##########################################################

        self.doma = {}              # тут дополнительно идут дома

    ##########################################################
        self.db_add()
        return self

    # Добавление дома (вместа аргументов идем по экстре)
    def add_dom(self):
        print (self.extra)
        # Функция вернет нам ид дома в базе
        if not self.doma:
            self.doma = {}
        self.doma[self.extra["name"]] = Dom.Create(self.extra, "%s_%s" % (self.host, self.id))
        # Заполним выход и обновим в базе
        self.menu = "menu"
        self.extra = {"name": self.extra["name"]}
        self.db_update()

    # Тут меняем
    def change_dom(self, *args):
        print(self.extra)
        DB_doma[self.doma[self.extra["name"]]].change(self.extra)
        self.menu = "menu"
        self.extra = {"name": self.extra["name"]}
        self.db_update()

    # Удаление дома
    def delete_dom(self, *args):
        print (self.extra)
        id = self.doma[self.extra["name"]]
        DB_doma[self.doma[self.extra["name"]]].delete()
        DB_doma.delete(id)
        del self.doma[self.extra["name"]]

        self.db_update()

    # Подтверждение оплаты
    def confirm_oplata(self):
        if self.extra:
            if "name" in self.extra:
                dom = DB_doma[self.doma[self.extra["name"]]]  # Дом
                if dom.kvartirant:
                    dom.kvartirant.last_oplata = datetime.datetime.now()
                    dom.kvartirant.db_event_update(self.host, self.id, dom.id)
                    dom.db_update()
                    return True
        else:
            return False





############################################################################
dom_args_text={                 # Текст для описания
    "adress": "Адрес: ",
    "square": "Площадь: ",
    "rooms": "Кол-во комнат: ",
    "sanuzel": "Санузел: ",
    "extras": "Удобства",
    "text": "Дополнительно: "
}
# Класс дома
class Dom:
    # Инит
    def __init__(self):
        self.name = ""                               # Имя
        self.id = 0                                  # ID, выдается базой данных
        self.owner_hostid = ""                       # На всякий привяжем владельца
        self.add_time = None                         # Время добавления

        self.adress = False                          # Адрес
        self.square = False                          # Площадь
        self.rooms = False                           # Кол-во комнат
        self.sanuzel = False                         # Санузел
        self.extras = {                              # Доп поля
            'холодильник': False,
            'телевизор': False,
            'стиралка': False,
            'кондиционер': False,
            'микроволновка': False,
            'приточная вентиляция': False,
            'посудомоечная машина': False,
            'мебель': False,
            'вид из окон': False,
        }
        self.text = False                            # Текст
        self.photos = False                          # Фоточки
        self.kvartirant = False                      # Тот кто снимает квартиру, если он есть

    # Создание из вне
    @staticmethod
    def Create(z, owner_hostid):
        self = Dom()
        self.name = z["name"]
        self.owner_hostid = owner_hostid
        self.add_time = datetime.datetime.now()

        for i in z:
            if z[i]:
                if i != "extras": # Если не экстра
                    self.__dict__[i] = z[i]
        if "extras" in z:
            if z["extras"]:
                extras = z["extras"].replace(",", " ").split()
                for i in self.extras:
                    if smiles.extras[i] in extras:
                        self.extras[i] = True

        self.id = self.db_add()
        DB_doma.add(self)
        return self.id

    # Изменение дома
    def change(self, z):
        for i in z:
            # Если фото удаляем
            if i == "photos" and (type(z[i]) != list and z[i] == "delet"):
                self.__dict__[i] = None
                continue
            # Если существует
            if z[i]:
                # И если это не экстра!!!
                if i != "extras":
                    self.__dict__[i] = z[i]
        # дальше работаем с экстрой
        if "extras" in z:
            if z["extras"]:
                extras = z["extras"].replace(",", " ").split()
                for i in self.extras:
                    if smiles.extras[i] in extras:
                        self.extras[i] = True
                    else:
                        self.extras[i] = False
        self.db_update()

    # Добавление нового в базу данных
    def db_add(self):
        vars = {}
        for i in self.__dict__:
            obj = self.__dict__[i]
            if obj:
                if type(obj) == dict or type(obj) == list:
                    vars[i] = ("'" + json.dumps(obj, ensure_ascii=False) + "'")
                elif type(obj) == Kvartirant:
                    vars[i] = ("'" + obj.drop() + "'")
                elif i == "add_time":
                    vars[i] = "'" + str(time_to_datetime(obj)) + "'"
                else:
                    vars[i] = "'" + str(obj) + "'"
        responce = '''INSERT INTO {0} ({1}) VALUES ({2}); '''.format(DOMA_TABLE,
                                                                   ",".join(vars.keys()), ",".join(vars.values()))
        print(responce)
        co, cu = connect()
        cu.execute(responce)
        co.commit()
        id = cu.getlastrowid()
        print (id)
        co.close()
        DB_doma.add(self)
        print("Дом %s добавлен как ид " % self.name, id)

        return id

    # Обновление в базе данных
    def db_update(self):
        vars = []
        for i in self.__dict__:
            obj = self.__dict__[i]
            if obj:
                if type(obj) == dict or type(obj) == list:
                    vars.append(i + "='" + json.dumps(obj, ensure_ascii=False) + "'")
                elif type(obj) == Kvartirant:
                    vars.append(i + "='" + obj.drop() + "'")
                elif i == "add_time":
                    vars.append(i + "='" + str(time_to_datetime(obj)) + "'")
                else:
                    vars.append(i + "='" + str(obj) + "'")
            else:
                vars.append("%s = NULL" % i)
        responce = '''UPDATE {0} SET {1} WHERE id = "{2}" '''.format(DOMA_TABLE,
                                                                             ",".join(vars)
                                                                             , self.id)
        print(responce)
        co, cu = connect()
        cu.execute(responce)
        co.commit()
        co.close()
        print("Дом %s обновлен!" % self.id)

    # Загрузка из БД
    @staticmethod
    def db_load(id):
        response = """SELECT * FROM {0} WHERE (id = "{1}")""".format(DOMA_TABLE, id)
        co, cu = connect()
        cu.execute(response)
        zis = cu.fetchall()[0]
        print (zis)
        zis = {DB_DOMA_SLOTS[i]: str(k) for i, k in enumerate(zis)}
        print(zis)
        co.close()
        self = Dom()

        # Заполняем поля
        for i in zis:
            # Если пустота
            if not zis[i]:
                continue
            # Если пустота
            elif zis[i] == "None":
                self.__dict__[i] = None
            # Время
            elif i == "add_time":
                self.__dict__[i] = datetime_to_time(zis[i])
            # Квартирант
            elif i == "kvartirant":
                self.__dict__[i] = Kvartirant.load(json.loads(zis[i],encoding="utf-8"))
            # Если словарь
            elif zis[i].strip().startswith("{") and zis[i].strip().endswith("}"):
                self.__dict__[i] = json.loads(zis[i],encoding="utf-8")
                print(json.loads(zis[i]))
            # Если массив
            elif zis[i].strip().startswith("[") and zis[i].strip().endswith("]"):
                self.__dict__[i] = json.loads(zis[i],encoding="utf-8")
                print(json.loads(zis[i]))
            # Если обычное значение
            else:
                self.__dict__[i] = zis[i]

        return self  # Возвращаем

    # Удаление из базы
    def delete(self):
        co, cu = connect()
        cu.execute("""DELETE FROM %s WHERE id=%s""" % (DOMA_TABLE, self.id))
        co.commit()
        co.close()

    # Добавление квартиранта
    def add_kvartirant(self, extra):
        host, id = self.owner_hostid.split("_")
        self.kvartirant = Kvartirant.Create(extra, host, id, self.id)

        self.db_update()

    # Изменение квартиранта
    def kvart_change(self, extra, *args):
        host, id = self.owner_hostid.split("_")
        self.kvartirant.change(extra, host, id, self.id)
        self.db_update()

    # Удаление квартиранта
    def del_kvartirant(self):
        self.kvartirant.delete()
        self.kvartirant = None
        self.db_update()

    # Текстовое представление
    def __str__(self):
        txt = "Квартира <<%s>>:\n\n" % self.name
        txt += "Адрес: %s\n" % self.adress
        txt += "Площадь: %s\n" % self.square
        txt += "Кол-во комнат: %s\n" % (self.rooms if self.rooms != "0" else "студия")
        if self.sanuzel == "0":
            txt += "Санузел: совместный\n"
        elif self.sanuzel == "1":
            txt += "Санузел: раздельный\n"
        else:
            txt += "Санузлы: %s\n" % self.sanuzel
        txt += "Удобства:\n"
        if self.extras:
            for i in self.extras:
                if self.extras[i]:
                    txt += smiles.tab + "%s\n" % i
        else: txt += smiles.tab + "не заявлено\n"

        txt += "Дополнительно: %s\n" % self.text

        if self.kvartirant:
            txt += "\n" + str(self.kvartirant)
        else:
            txt += "\n" + "Квартирант: нет"

        return txt.replace("False", "не указано").replace("None", "не указано")



########################################################################################################################
# Ответственная за экономию памяти подгружающе/удаляющие объекты

LOG_LENGTH = 50
_user_db_store = {"vk": {}}
_user_db_log = {"vk": []}
_user_db_index = {"vk": []}
# Считаем что у нас есть
co, cu = connect()
cu.execute("SELECT id, host FROM %s" % USER_TABLE)
for i in cu.fetchall():
    _user_db_index[i[1]].append(i[0])
co.close()

# Класс который держит некоторый пул
class UsersDB:
    def __init__(self):
        global _user_db_store, _user_db_log, _user_db_index
        self.store = _user_db_store
        self.log = _user_db_log
        self.index = _user_db_index

    # Чтобы при удалении все обновлялось (типа деструктор)
    def destruct(self):
        print ("Дропаем юзеров")
        for i in self.store:
            for j in self.index[i]:
                if j in self.store[i]:
                    try:
                        self.store[i][j].db_update()
                        del self.store[i][j]
                    except Exception as exp:
                        print (exp)

    # Добавление нового изнутри
    def add(self, item):
        self.index[item.host].append(item)
        self.store[item.host][item.id] = item
        self.log[item.host].insert(0, item)

    # Получение элемента из стора
    def get(self, host, item):
        # Если еще не скачано, то мы скачаем
        if not item in self.store[host]:
            self.store[host][item] = User.db_load(item,"vk")
        # Пустим это в лог и вернем
        self.log_update(host, id)
        return self.store[host][item]

    # Стандартное задние по индексу
    def set(self, host, key, value):
        self.store[host][key] = value
        self.log_update(host, key)
        if not key in self.index[host]:
            self.index[host].append(key)

    # Содержится ли в сторе
    def contains(self, host, item):
        self.log_update(host, item)
        return item in self.index[host]

    # Выгрузка юзера
    def dump(self, host, item):
        # Проверяем если этот пользователь есть в базе
        if self.store[host][item]:
            self.store[host][item].db_update()
        del self.store[host][item]
        self.log[host] = [x for x in self.log[host] if x != item]

    # Тут мы пишем в лог что используем этого пользователя
    def log_update(self, host, id):
        try:
            self.log[host].pop(self.log[host].index(id))  # Вытащим из лога
        except:
            pass
        self.log[host].insert(0, id)            # И в начало
        # Тут мы смотрим лог и если у нас в памяти больше скольки то пользвоателей, мы дропаем их
        for host in self.log:
            if len(self.log[host]) > LOG_LENGTH:
                for i in self.log[host][LOG_LENGTH:]:
                    # Проверяем если этот пользователь есть в базе
                    self.dump(host, i)
            self.log[host] = self.log[host][:LOG_LENGTH]


# Тот же класс, но дял в без доп аргументов
class UserDB_vk():
    def __init__(self, main):
        self.main = main

    # Destructor
    def destruct(self):
        self.main.destruct()

    def dump(self, i):
        self.main.dump("vk", i)

    # Индексатор с одним значением
    def __getitem__(self, item):
        return self.main.get("vk", item)

    # Индексатор
    def __setitem__(self, key, value):
        self.main.set("vk", key, value)

    # Контейнс
    def __contains__(self, item):
        return self.main.contains("vk", item)


# Переменные
DB_users = UsersDB()
DB_users_vk = UserDB_vk(DB_users)   # Вкшная

##############################################################
# Тут будет типа пула для домов
_doma_db_store = {} # Стор
_doma_db_log = []   # Логи
_doma_db_index = [] # Индекс
# Считаем что у нас есть
co, cu = connect()
cu.execute("SELECT id FROM %s" % DOMA_TABLE)
for i in cu.fetchall():
    _doma_db_index.append(i[0])
class DomaDB:
    def __init__(self):
        global _doma_db_store, _doma_db_log, _doma_db_index
        self.store = _doma_db_store
        self.log = _doma_db_log
        self.index = _doma_db_index

    # Добавление нового изнутри
    def add(self, item):
        self.index.append(item)
        self.store[item.id] = item
        self.log.insert(0, item)

    def delete(self, id):
        if id in self.index:
            self.index.pop(self.index.index(id))
            del self.store[id]
            self.log.pop(self.log.index(id))

    # Индексатор получения
    def __getitem__(self, item):
        # Аналогичто с юзерами
        if not item in self.store:
            self.store[item] = Dom.db_load(item)
        self.log_update(item)
        return self.store[item]

    # Контейнер
    def __contains__(self, item):
        self.log_update(item)
        return item in self.index

    # Работа с логом (не просто же он так)
    def log_update(self, id):
        try:
            self.log.pop(self.log.index(id))  # Вытащим из лога
        except:
            pass
        self.log.insert(0, id)            # И в начало
        # Тут мы смотрим лог и если у нас в памяти больше скольки то пользвоателей, мы дропаем их
        if len(self.log) > LOG_LENGTH:
            for i in self.log[LOG_LENGTH:]:
                self.store[i].db_update()
                del self.store[i]
        self.log = self.log[:LOG_LENGTH]


# И создадим объект
DB_doma = DomaDB()
########################################################################################################################
# Здесь класс квартирантов
class Kvartirant:
    def __init__(self):
        self.name = ""                      # Имя
        self.contacts = {                   # Контакты
            "telephone": None,
            "email": None,
            "vk": None
        }
        self.oplata = {                     # Оплата
            "period": None,                     # Периодичность
            "summa": None,                      # Сумма
            "sposob": None                      # Способ
        }
        self.last_oplata = None             # Последняя оплата
        self.dogovor = {                    # Договор
            "gorod": None,  # Город
            "start_date": None,                 # Начало
            "end_date": None                    # Конец
        }
        self.text = None                    # Дополнительная информация

        # События когда нужно прислать уведомления
        self.event = {"end_date":None, "oplata":None}
        #[номер в базе, дата, кол - во выполнений]

    # Удалятор
    def delete(self):
        Ns = []
        if self.event:
            if self.event["end_date"]:
                Ns.append(self.event["end_date"][0])
            if self.event["oplata"]:
                Ns.append(self.event["oplata"][0])

        for i in Ns:
            self.db_delete_event(i)

    # Статическое создание
    @staticmethod
    def Create(z, host, id, dom=None):
        self = Kvartirant()

        self.name = z["name"]                    # Имя
        if "telephone" in z:
            self.contacts["telephone"] = z["telephone"]
        if "email" in z:
            self.contacts["email"] = z["email"]
        if "vk" in z:
            self.contacts["vk"] = z["vk"]

        if "period" in z:
            self.oplata["period"] = z["period"]
        if "summa" in z:
            self.oplata["summa"] = z["summa"]
        if "sposob" in z:
            self.oplata["sposob"] = z["sposob"]

        if "last_oplata" in z:
            self.last_oplata = z["last_oplata"]

        if "start_date" in z:
            self.dogovor["start_date"] = z["start_date"]
        if "end_date" in z:
            self.dogovor["end_date"] = z["end_date"]
        if "gorod" in z:
            self.dogovor["gorod"] = z["gorod"]
        if "text" in z:
            self.text = z["text"]

        self.db_event_create(host, id, dom)
        return self

    # Тут мы изменяем
    def change(self, z, host, id, dom=None):
        if "name" in z:
            if z["name"]:
                self.name = z["name"]
        if "telephone" in z:
            if z["telephone"]:
                self.contacts["telephone"] = z["telephone"]
        if "email" in z:
            if z["email"]:
                self.contacts["email"] = z["email"]
        if "vk" in z:
            if z["email"]:
                self.contacts["vk"] = z["vk"]

        if "period" in z:
            if z["period"]:
                self.oplata["period"] = z["period"]
        if "summa" in z:
            if z["summa"]:
                self.oplata["summa"] = z["summa"]
        if "sposob" in z:
            if z["sposob"]:
                self.oplata["sposob"] = z["sposob"]

        if "last_oplata" in z:
            if z["last_oplata"]:
                self.last_oplata = z["last_oplata"]

        if "start_date" in z:
            if z["start_date"]:
                self.dogovor["start_date"] = z["start_date"]
        if "end_date" in z:
            if z["end_date"]:
                self.dogovor["end_date"] = z["end_date"]
        if "gorod" in z:
            if z["gorod"]:
                self.dogovor["gorod"] = z["gorod"]
        if "text" in z:
            if z["text"]:
                self.text = z["text"]

        self.db_event_update(host, id, dom)
        return self

    # Загрузка элемента
    @staticmethod
    def load(stor):
        self = Kvartirant()

        for i in stor:
            self.__dict__[i] = stor[i]
        # Тоже костыль с дататаймом
        if self.last_oplata:
            self.last_oplata = datetime_to_time(self.last_oplata)
        if self.dogovor["start_date"]:
            self.dogovor["start_date"] = datetime_to_time(self.dogovor["start_date"])
        if self.dogovor["end_date"]:
            self.dogovor["end_date"] = datetime_to_time(self.dogovor["end_date"])

        #   запишем в ивент
        if not self.event:
            self.event = {"end_date": None, "oplata": None}

        return self

    # Дроп в жсон
    def drop(self):
        js = copy.deepcopy(self.__dict__) # Костыль с даттаймом
        js["last_oplata"] = time_to_datetime(js["last_oplata"])
        js["dogovor"]["start_date"] = time_to_datetime(js["dogovor"]["start_date"])
        js["dogovor"]["end_date"] = time_to_datetime(js["dogovor"]["end_date"])
        return json.dumps(js, ensure_ascii=False)

    # Текстовое представление
    def __str__(self):
        txt = ""
        txt += "ФИО: %s\n" % self.name
        if self.dogovor:
            txt += "Договор от %s до %s" % (time_to_date(self.dogovor["start_date"]),
                                            time_to_date(self.dogovor["end_date"])) + "\n"
        if any(self.contacts[i] for i in self.contacts):
            txt += "Контакты владельца:\n"
            if self.contacts["telephone"]:
                txt += smiles.tab + self.contacts["telephone"] + "\n"
            if self.contacts["email"]:
                txt += smiles.tab + self.contacts["email"] + "\n"
            if self.contacts["vk"]:
                txt += smiles.tab + self.contacts["vk"] + "\n"
        txt += "Дата последней оплаты: %s\n" % time_to_date(self.last_oplata)
        txt += "Периодичность оплаты: %s\n" % (self.oplata["period"] if self.oplata["period"] != "0.5" else "0.5")
        txt += "Размер оплаты: %s\n" % self.oplata["summa"]
        txt += "Способ оплаты: %s\n" % self.oplata["sposob"]
        txt += "Дополнительная информация: %s\n" % self.text

        return txt.replace("None", "*не указано*")

    # РАбота с днями
    def date_fix(self, d,m,y):
        if d > 30:
            d = d % 30
            m+= d // 30
        elif d <=0:
            d = abs(d) % 30
            m -= abs(d) // 30

        if m > 12:
            m = m % 12
            y += m // 12
        elif m <=0:
            m = abs(m) % 12
            y -= abs(m) // 12

        return (y,m,d) # чтобы развернуть

    # Добавление ивента
    def db_event_create(self, host, id, dom=None):
        # Создаем
        if self.dogovor["end_date"]:
            self.db_create_event_end_date(host,id, dom)
        # И этот
        if self.last_oplata and self.oplata["period"]:
            self.db_create_event_oplata(host,id, dom)

    # Если мы что то обновили вызовим вот это проверить
    def db_event_update(self, host, id, dom=None):
        print("АПДЕЙТ")
        # Загрузим че есть
        co, cu = connect()
        cu.execute("SELECT * FROM %s where host='%s' and id='%s'" % (EVENTS_TABLE, host, id))
        # Снизу сложно
        R = cu.fetchall()
        co.close()
        if R:
            # Формируем словарь по ключам таблицы (отсекаем другой тип)
            db_events = {x[0]: dict(N=x[0], time=x[1], host=x[2], id=x[3], message=x[4], dom=x[5]) for x in R if x[5] == dom}
        else:
            db_events = {}

        # Для end date
        end_date = self.event["end_date"]
        if end_date:
            if end_date[1] == time_to_DBdate(self.dogovor["end_date"]) and end_date[0] in db_events:
                print("Увадомление о end_date в норме")
                del db_events[end_date[0]]
            else:
                print("Перезапишем увадомление об end_date")
                self.db_delete_event(end_date[0])
                self.db_create_event_end_date(host,id, dom)

        elif self.dogovor["end_date"]:
            self.db_create_event_end_date(host,id, dom)


        # для периода
        oplata = self.event["oplata"]
        if oplata:
            if oplata[1] == time_to_DBdate(self.last_oplata) and oplata[0] in db_events:
                print("Увадомление о oplata в норме")
                del db_events[oplata[0]]
            else:
                print("Перезапишем увадомление об oplata")
                self.db_delete_event(oplata[0])
                self.db_create_event_oplata(host, id, dom)

        elif self.last_oplata and self.oplata["period"]:
            self.db_create_event_oplata(host,id, dom)

        # Чистим левые по этому акку
        if len(db_events):
            print("остались лишние: ", str(db_events))
            for i in db_events:
                self.db_delete_event(i)

    # Проверка валидности события
    def isvalid(self, event):
        if event["message"] == "end_date":
            end_date = self.event["end_date"]
            # Если ключ совпадает
            return (end_date[0] == event["N"])

        elif event["message"] == "oplata":
            oplata = self.event["oplata"]
            # Возвращаем валидность
            return (oplata[0] == event["N"])

        # На всякий случай
        return False

    # Доабвление сообщения об окончании срока договора
    def db_create_event_end_date(self, host, id, dom=None, number=None):
        # Вары
        vars = dict(host="'"+host+"'", id="'"+id+"'", message="'end_date'")
        if dom:
            vars["dom"] = "'%s'" % dom

        tm = self.dogovor["end_date"]
        # Анализируем сколько дней до оплаты и исходя из этого делаем новый ивент
        delta = (tm - datetime.datetime.now()).days
        # Если больше 15
        if delta > 15:
            number = -15
        elif delta > 10:
            number = -10
        elif delta > 5:
            number = -5
        elif delta >=1:
            number = -1
        # Если просрочили напоминаем
        elif number == None:
            number = 0
        # и каждые 5 дней
        else:
            number = abs(delta) + 5

        dt = tm
        if number:
            dt += datetime.timedelta(days=number)

        vars["time"] = "'"+time_to_DBdate(dt)+"'" # Чтобы все по форме

        # И пишем в базу
        co, cu = connect()
        txt = """INSERT INTO {0} ({1}) VALUES ({2})""".format(EVENTS_TABLE, ",".join(vars.keys()),
                                                        ",".join(vars.values()))
        print (txt)
        cu.execute(txt)
        co.commit()
        N = cu.getlastrowid()
        co.close()
        # Записываем это как [номер в базе, дата, кол-во выполнений]
        # Дата чтобы при изменении проверить поменялось ли
        self.event["end_date"] = [N, time_to_DBdate(self.dogovor["end_date"]), number]

        print("Добавлено уведомление '%d' об окончании на " % N, time_to_DBdate(dt))

    # Добавление сообщения об оплате
    def db_create_event_oplata(self, host, id, dom=None, number=None):
        vars = dict(host="'" + host + "'", id="'" + id + "'", message="'oplata'")
        if dom:
            vars["dom"] = "'%s'" % dom

        tm = self.last_oplata     # Дата
        period = float(self.oplata["period"]) # период
        # Анализируем сколько дней до оплаты и исходя из этого делаем новый ивент
        delta = ((tm + datetime.timedelta(weeks=4*period)) - datetime.datetime.now()).days
        if delta > 10 and period > 1:
            number = 10
        elif delta > 5:
            number = 5
        elif delta >= 1:
            number = 1
        # Если просрочили
        elif number == None:
            number = 0
        # И каждые 5 дней от сегодня
        else:
            number = (datetime.datetime.now() - tm).days + 5

        dt = tm
        if number:
            dt += datetime.timedelta(days=number)

        vars["time"] = "'"+time_to_DBdate(dt)+"'"  # Чтобы все по форме

        # И пишем в базу
        co, cu = connect()
        txt = """INSERT INTO {0} ({1}) VALUES ({2})""".format(EVENTS_TABLE, ",".join(vars.keys()),
                                                                   ",".join(vars.values()))
        cu.execute(txt)
        print (txt)
        co.commit()
        N = cu.getlastrowid()
        co.close()
        # Записываем это как [номер в базе, дата, кол-во выполнений]
        # Дата чтобы при изменении проверить поменялось ли
        self.event["oplata"] = [N, time_to_DBdate(self.last_oplata), number]

        print("Добавлено уведомление '%d' об оплате на " % N, time_to_DBdate(dt))

    # Удаление уведомления
    def db_delete_event(self, N):
        print("Удаялем ", N)
        co, cu = connect()
        cu.execute("DELETE FROM %s WHERE N = %s" % (EVENTS_TABLE, N))
        co.commit()
        co.close()

