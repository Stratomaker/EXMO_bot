# coding: utf8
import urllib, http.client
import time
import json
import hmac, hashlib
import keys

API_KEY = keys.API_KEY
API_SECRET = keys.API_SECRET

CURRENCY_1 = 'BTC' 
CURRENCY_2 = 'USD'

CURRENCY_1_MIN_QUANTITY = 0.001 # минимальная сумма ставки по первой валюте - берется из https://api.exmo.com/v1/pair_settings/
CURRENCY_2_MIN_QUANITY = 0.001 #минимльная сумма ставки по второй валюте

ORDER_LIFE_TIME = 3 # через сколько минут отменять неисполненный ордер на покупку CURRENCY_1
STOCK_FEE = 0.002 # Комиссия, которую берет биржа (0.002 = 0.2%)
AVG_PRICE_PERIOD = 15 # За какой период брать среднюю цену (мин)
CAN_SPEND = 5 # Сколько тратить CURRENCY_2 каждый раз при покупке CURRENCY_1
PROFIT_MARKUP = 0.001 # Какой навар нужен с каждой сделки? (0.001 = 0.1%)
DEBUG = True # True - выводить отладочную информацию, False - писать как можно меньше

STOCK_TIME_OFFSET = 0 # Если расходится время биржи с текущим 

API_URL = 'api.exmo.com'
API_VERSION = 'v1'

class ScriptError(Exception):
    pass
class ScriptQuitCondition(Exception):
    pass

CURRENT_PAIR = CURRENCY_1 + '_' + CURRENCY_2

def call_api(api_method, http_method="POST", **kwargs):
    payload = {'nonce': int(round(time.time()*1000))}

    if kwargs:
        payload.update(kwargs)

    payload =  urllib.parse.urlencode(payload)

    H = hmac.new(key=API_SECRET, digestmod=hashlib.sha512)
    H.update(payload.encode('utf-8'))
    sign = H.hexdigest()
   
    headers = {"Content-type": "application/x-www-form-urlencoded",
           "Key":API_KEY,
           "Sign":sign}

    conn = http.client.HTTPConnection(API_URL, timeout=60)
    conn.request(http_method, "/"+API_VERSION + "/" + api_method, payload, headers)
    response = conn.getresponse().read()
    conn.close()

    try:
        obj = json.loads(response.decode('utf-8'))
        if 'error' in obj and obj['error']:
            raise ScriptError(obj['error'])
        return obj
    except ValueError:
        raise ScriptError('Ошибка анализа возвращаемых данных, получена строка', response)

def check_sell_orders():
        try:
            opened_orders = call_api('user_open_orders')[CURRENT_PAIR]
        except KeyError:
            print('Открытых ордеров нет')
            opened_orders = []
            
        sell_orders = []
        # Есть ли неисполненные ордера на продажу CURRENCY_1?
        for order in opened_orders:
            if order['type'] == 'sell':
                # Есть неисполненные ордера на продажу CURRENCY_1, выход
                raise ScriptQuitCondition('Выход, ждем пока не исполнятся/закроются все ордера на продажу (один ордер может быть разбит биржей на несколько и исполняться частями)')
            else:
                # Запоминаем ордера на покупку CURRENCY_1
                sell_orders.append(order)
                
        # Проверяем, есть ли открытые ордера на покупку CURRENCY_1
        if sell_orders: # открытые ордера есть
            for order in sell_orders:
                # Проверяем, есть ли частично исполненные
                print('Проверяем, что происходит с отложенным ордером', order['order_id'])
                try:
                    order_history = call_api('order_trades', order_id=order['order_id'])
                    # по ордеру уже есть частичное выполнение, выход
                    raise ScriptQuitCondition('Выход, продолжаем надеяться докупить валюту по тому курсу, по которому уже купили часть')
                except ScriptError as e:
                        print('Частично исполненных ордеров нет')
                    
                        time_passed = time.time() + STOCK_TIME_OFFSET*60*60 - int(order['created'])

                        if time_passed > ORDER_LIFE_TIME * 60:
                            # Ордер уже давно висит, никому не нужен, отменяем
                            call_api('order_cancel', order_id=order['order_id'])
                            raise ScriptQuitCondition('Отменяем ордер -за ' + str(ORDER_LIFE_TIME) + ' минут не удалось купить '+ str(CURRENCY_1))
                        else:
                            raise ScriptQuitCondition('Выход, продолжаем надеяться купить валюту по указанному ранее курсу, со времени создания ордера прошло %s секунд' % str(time_passed))
                else:
                        raise ScriptQuitCondition(str(e))

def market_stats():
    try:
        INPUT_PAIR = input('введите желаемую валютную пару в формате BTC_USD:\n')
        stats = call_api('ticker')[INPUT_PAIR]
    except KeyError:
        print('введеной пары не существует')
        stats = []
    for stat in stats:
        print(stat, ' ', stats[stat])

def balance(): #aaaa
	balances = call_api('user_info')['balances'] #aaaa
	for balance in balances: #aaaa
		print(balance,': ',balances[balance],'\n') #aaaa


def reader(command):
    if command == 'check_sell':
        check_sell_orders()
    elif command == 'check_stats': 
        market_stats() 
    elif command == 'check_balance': #aaaa
    	balance() #aaaa
    else:
        print('комманда еще не прописана')

# Главный цикл
def main_flow():
    
    try:
        command = input()
        reader(command)
        
    except ScriptError as e:
        print(e)
    except ScriptQuitCondition as e:
        print(e)
        pass
    except Exception as e:
        print("!!!!",e)

while(True):
    main_flow()
    time.sleep(1)