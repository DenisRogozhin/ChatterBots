# -*- coding: utf-8 -*-


from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
import random

with open('Token.txt', 'r',encoding='utf-8') as ftoken:
    Token= ftoken.read()


bot = Bot(token=Token)
dp = Dispatcher(bot, storage=MemoryStorage())


class Botstates(StatesGroup):
    st_start = State()
    st_wait_who = State()
    st_wait_word = State()
    st_word_for_letter = State()


with open('namegorod.txt', 'r', encoding='utf-8') as f:
    true_names = f.read().split('\n')[:-1]
g_vocab = [gn.lower() for gn in true_names]


game_parameters_by_id = dict({})


class Game_parameters:
    def __init__(self):
        self.g_score = []
        self.user_names = []  # список использованных пользователем городов/слов
        self.leftover_names = true_names.copy()  # вычеркивать имена, чтоб когда-то заканчивалось, по id список еще неиспользованных ботом городов
        self.extra_names_learned = []  # используем предыдущие предложения человека против него, забываем по reset
        self.latest_letter = ''  # хотела через состояния но 31 одинаковое состояние, удивительно, оказалось не так красиво как казалось

    def curr_score(self):
        return "Вы: " + str(self.g_score[0]) + " - Я: " + str(self.g_score[1])


@dp.message_handler(commands=['start'], state='*')
async def proc_com_start(message: types.Message):
    if game_parameters_by_id.get(message.from_user.id) == None: game_parameters_by_id[   message.from_user.id] = Game_parameters()  # по id пустые словари слов
    await bot.send_message(message.from_user.id, "Сыграем в города!")
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if game_parameters_by_id[message.from_user.id].g_score != []:
        buttons = ["Я", "Ты", "Счет"]
    else:
        buttons = ["Я", "Ты"]
    keyboard.add(*buttons)
    await bot.send_message(message.from_user.id, "Кто начинает?", reply_markup=keyboard)
    await Botstates.st_wait_who.set()


# получение индекса первой с конца слова "значащей" буквы в слове, выбираемом ботом
def lastletter_bot( s):  # более мягкие правила, т.к. наверняка нет плохих вариантов после проверки по получении слова lastletter_user, цикл с конца где-то да закончится, и пустых нет
    ll = s[len(s) - 1]
    if ((ll == 'ъ' or ll == 'ь') and (len(s) > 1)):  # ищем первую с конца приемлемую букву
        kl = len(s) - 2
        while (kl >= 0):
            if (s[kl] != 'ъ') and (s[kl] != 'ь'):
                ll = s[kl]
                break
            kl -= 1
        return kl
    else:
        return len(s) - 1


# получение индекса первой с конца слова "значащей" буквы в слове, присланном пользователем (может быть гораздо более странным чем выбираемое ботом из своих)
def lastletter_user(s):
    ll = s[len(s) - 1]
    if ((ll == 'ъ' or ll == 'ь') and (len(s)) > 1):  # ищем первую с конца приемлемую букву
        kl = len(s) - 2
        while (kl >= 0):
            if (s[kl] != 'ъ') and (s[kl] != 'ь'):
                ll = s[kl]
                break
            kl -= 1
        if kl < 0: return -1
        if (s[kl] <= 'я') and (s[kl] >= 'а') and (s[kl] != 'ь') and (s[kl] != 'ъ'):  # между 'а' и 'я' и не 'ъ' 'ь'
            return kl  # нашли где  в списке дозволенных русских букв, с другими языками не работаем
        return -1  # даже первая с конца которая уже не ь\ъ неподходящая
    else:
        return len(s) - 1


@dp.message_handler(commands=['reset'], state='*')  # сброс прогресса вообще. мало ли хочется заново счет вести, или заставить забыть твои города
async def proc_com_progress_reset(message: types.Message, state: FSMContext):
    game_parameters_by_id[message.from_user.id] = Game_parameters()
    await bot.send_message(message.from_user.id, "Начнем с чистого листа!")
    # keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    await bot.send_message(message.from_user.id, "Если захотите поиграть, введите /start")
    await Botstates.st_start.set()


@dp.message_handler(commands=['exit'],  state='*')  # то же самое что и логика "сдаюсь" но командой, формально. Одинаково для всех состояний- просто сброс прогресса текущей игры без чьей-то победы
async def proc_com_exit(message: types.Message, state: FSMContext):
    if game_parameters_by_id[message.from_user.id].g_score != []:
        await bot.send_message(message.from_user.id, "Игра отменена. Текущий счет: " + game_parameters_by_id[  message.from_user.id].curr_score())
    # keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    await bot.send_message(message.from_user.id, "Если захотите еще поиграть, введите /start")
    await Botstates.st_start.set()


@dp.message_handler(state=Botstates.st_wait_who)
async def proc_word_who(message: types.Message, state: FSMContext):  # контекст для словарей по id и списка слов
    msg = message.text.lower()
    if (msg == 'ты') or (msg == 'вы'):
        await bot.send_message(message.from_user.id, "Отлично! Начинаю:")

        game_parameters_by_id[message.from_user.id].user_names = []  # нужно сбрасывать каждую игру
        if game_parameters_by_id[message.from_user.id].g_score == []: game_parameters_by_id[   message.from_user.id].g_score = [0,  0]  # счета не существует вообще пока формально не начата первая игра - не выбрано кто первый идет
        game_parameters_by_id[message.from_user.id].leftover_names = true_names.copy() + game_parameters_by_id[    message.from_user.id].extra_names_learned.copy()  # из чего бот выбирает и откуда использованные выкидывает

        # выбираем свое первое слово случайно
        k = random.randint(0,len(game_parameters_by_id[message.from_user.id].leftover_names)-1)
        wk = game_parameters_by_id[message.from_user.id].leftover_names[k]
        game_parameters_by_id[message.from_user.id].leftover_names.remove(  wk)  # исключить из своего списка
        ll = lastletter_bot(wk.lower())  # первая не ь/ъ, приемлемы тольок рус. буквы
        game_parameters_by_id[message.from_user.id].latest_letter = wk[ll]

        buttons = ["Счет", "Сдаюсь"]
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(*buttons)
        await bot.send_message(message.from_user.id, wk, reply_markup=keyboard)  # само слово-то надо отправить
        await Botstates.st_word_for_letter.set()
    elif (msg == 'я'):
        # запоминаем предожениея пользователя и используем против него же, если их в исходном словаре не было
        game_parameters_by_id[ message.from_user.id].user_names = []  # сброс на  новую игру - запрет для пользователя пустой

        if game_parameters_by_id[message.from_user.id].g_score == []: game_parameters_by_id[    message.from_user.id].g_score = [0, 0]  # user,bot  #после этого состояния всегда точно будет существовать gscore
        buttons = ["Счет",  "Сдаюсь"]  # условно считаем что теперь уж игра началась, и счет появился, но в состоянии ожидания первого слова отказ еще не считается за проигрыш
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(*buttons)
        await bot.send_message(message.from_user.id, "Хорошо, начинайте!", reply_markup=keyboard)
        await Botstates.st_wait_word.set()
    elif (msg == 'счет') or (   msg == 'результат'):  # надеюсь что "счет","нет" или "сдаюсь" не могут быть именами населенных пунктов
        # выводит, сост не меняет, ничего не меняет
        if game_parameters_by_id[message.from_user.id].g_score != []:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            buttons = ["Я", "Ты", "Счет"]
            keyboard.add(*buttons)
            await bot.send_message(message.from_user.id, game_parameters_by_id[message.from_user.id].curr_score(),    reply_markup=keyboard)
        else:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            buttons = ["Я", "Ты"]
            keyboard.add(*buttons)
            await bot.send_message(message.from_user.id, "Мы еще ни разу не начинали играть", reply_markup=keyboard)
    elif (msg == 'сдаюсь') or (msg == 'нет') or (
            msg == 'я сдаюсь'):  # ничего не меняется, просто идем обратно в start. Технически по кнопкам этого произойти не может, но пускай будут предусмотрены особые ответы на ручной ввод
        await bot.send_message(message.from_user.id, "Но мы же еще даже не начали...")
        if game_parameters_by_id[message.from_user.id].g_score != []:
            await bot.send_message(message.from_user.id,    "Текущий счет: " + game_parameters_by_id[message.from_user.id].curr_score())
        await bot.send_message(message.from_user.id, "Если захотите еще поиграть, введите /start")
        await Botstates.st_start.set()
    else:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        if game_parameters_by_id[message.from_user.id].g_score != []:
            buttons = ["Я", "Ты", "Счет"]
        else:
            buttons = ["Я", "Ты"]
        keyboard.add(*buttons)
        await bot.send_message(message.from_user.id, "Что-то я не понимаю... так вы начинаете или я?", reply_markup=keyboard)


@dp.message_handler(     state=Botstates.st_wait_word)  # получаем слово, если есть норм последняя буква, (если не знали(vocab+learned) - добавляем себе в learned), то ищем у себя по букве, не находим - сдаемся(счет+1), находим - удаляем,выводим,по букве в состояние
async def proc_first_word(message: types.Message, state: FSMContext):
    msg = message.text.lower()
    if (msg == 'счет') or (msg == 'результат'):
        if game_parameters_by_id[message.from_user.id].g_score != []:
            buttons = ["Счет", "Сдаюсь"]
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.add(*buttons)
            await bot.send_message(message.from_user.id, game_parameters_by_id[message.from_user.id].curr_score(),   reply_markup=keyboard)
        else:
            buttons = ["Сдаюсь"]
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.add(*buttons)
            await bot.send_message(message.from_user.id, "Мы еще ни разу не играли.",   reply_markup=keyboard)  # технически кнопка "счет" недоступна, но хочется предусмотреть ручное
    elif (msg == 'сдаюсь') or (msg == 'нет') or (msg == 'я сдаюсь'):  # ничего не меняется, просто идем обратно в start
        await bot.send_message(message.from_user.id, "Мы же только начали... Ну ладно, как хотите.")
        await bot.send_message(message.from_user.id,  "Текущий счет: " + game_parameters_by_id[message.from_user.id].curr_score())
        await bot.send_message(message.from_user.id, "Если захотите еще поиграть, введите /start")
        await Botstates.st_start.set()
    elif len(msg) > 0:
        if isword(msg):  # самое первое слово - не нужно проверять на повторение слова, присланного пользователем
            ll = lastletter_user(msg)  # ищем первую последнюю букву на которую нужно слово
            if ll == -1:
                await bot.send_message(message.from_user.id,  "Я знаю только названия городов на русском языке! Пожалуйста, используйте русский.")
            else:
                # новое ли для нас слово? по исходным и новым выученным
                if (msg not in [en.lower() for en in     game_parameters_by_id[message.from_user.id].extra_names_learned]) and (   msg not in g_vocab):  # g_vocab - исходные имена из файла в ниж.регистре, чтоб не каждый раз переделывать список, который по определению никогда не меняется
                    game_parameters_by_id[message.from_user.id].extra_names_learned.append( message.text)  # запоминаем новое слово на будущее
                    game_parameters_by_id[message.from_user.id].leftover_names.append(message.text)
                    game_parameters_by_id[message.from_user.id].user_names.append(msg)
                ll_names = [gn for gn in game_parameters_by_id[message.from_user.id].leftover_names if  gn[0].lower() == msg[ll]]  # выбираем из своих по первой букве
                if len(  ll_names) == 0:  # больше не знает слов на нужную букву - это и есть проигрыш, когда не можешь назвать не повторяясь слово
                    game_parameters_by_id[message.from_user.id].g_score[  0] += 1  # бот не смог найти слово - выиграл пользователь
                    await bot.send_message(message.from_user.id,    "Я не знаю больше слов на букву '" + msg[ll] + "'. Вы выиграли!")
                    await bot.send_message(message.from_user.id,    "Текущий счет: " + game_parameters_by_id[message.from_user.id].curr_score())
                    await bot.send_message(message.from_user.id, "Если захотите еще поиграть, введите /start")
                    await Botstates.st_start.set()
                else:  # еще есть неиспользованные слова на нужную букву

                    k = random.randint(  0,  len(ll_names)-1)  # random first word выбираем с нужной первой буквой как последняя у присланного
                    wk = ll_names[k]
                    game_parameters_by_id[message.from_user.id].leftover_names.remove(
                        wk)  # исключить из своего списка. Регистр сохранен, не будет несовпадений. Так как брали точно как там было, не должно ошибок получаться по отсутствию
                    ll = lastletter_bot(wk.lower())  # первая не ь/ъ, русская буква
                    game_parameters_by_id[message.from_user.id].latest_letter = wk[ll]

                    buttons = ["Счет", "Сдаюсь"]
                    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    keyboard.add(*buttons)
                    await bot.send_message(message.from_user.id, wk, reply_markup=keyboard)
                    await Botstates.st_word_for_letter.set()
        else:
            buttons = ["Счет", "Сдаюсь"]
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.add(*buttons)
            await bot.send_message(message.from_user.id, "Я практически уверен, что это не может быть приемлемым словом. Давайте что-нибудь другое придумайте.",   reply_markup=keyboard)
    else:
        buttons = ["Счет", "Сдаюсь"]
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(*buttons)
        await bot.send_message(message.from_user.id, "Не молчите, в молчании нет букв", reply_markup=keyboard)


def isword(  s):  # да, есть один город, оканчивающийся на !. Но знаете ли вы его?  А так кроме букв и "-"  в названиях городов на русском ничего нет. Ограничение чтоб всякие предложения не предлагали.
    if s == 'сен-луи-дю-ха!' or s == 'сен-луи-дю-ха! ха!': return True
    if (s[0] != '-') and (s[len( s) - 1] != '-'):  # не начинается/кончается с -, единственный знак препинания встречающийся в (большинстве?) русских наименованиях городов
        sn = s.replace('-', '').replace(' ', '').replace('ё', '')
        for i in range(ord('а'), ord('я') + 1):
            sn = sn.replace(chr(i), '')
        if len(sn) == 0: return True
    return False


# ожидание после слова с определенной последней буквой слова с определенной первой буквой
@dp.message_handler(state=Botstates.st_word_for_letter)
async def proc_word_for_letter(message: types.Message, state: FSMContext):
    msg = message.text.lower()
    if (msg == 'сдаюсь') or (msg == 'нет') or (msg == 'я сдаюсь'):
        game_parameters_by_id[message.from_user.id].g_score[1] += 1
        await bot.send_message(message.from_user.id,  "В таком случае эта игра закончена. Возможно в следующий раз вы выйдете победителем.")
        await bot.send_message(message.from_user.id,    "Текущий счет: " + game_parameters_by_id[message.from_user.id].curr_score())
        await bot.send_message(message.from_user.id, "Если захотите еще поиграть, введите /start")
        await Botstates.st_start.set()  # ничего кроме счета и старта там не обрабатывается осмысленно, вроде так это работает?
    elif (msg == 'счет') or (msg == 'результат'):
        buttons = ["Счет", "Сдаюсь"]
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(*buttons)
        await bot.send_message(message.from_user.id, game_parameters_by_id[message.from_user.id].curr_score(),  reply_markup=keyboard)
    else:
        if len(msg) > 0:
            if isword(msg):
                if msg in game_parameters_by_id[ message.from_user.id].user_names:  # смысл хранить слова - следование правилам неповтора, хотя если это ПЕРВОЕ слово то проверять нет смысла
                    buttons = ["Счет", "Сдаюсь"]
                    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    keyboard.add(*buttons)
                    await bot.send_message(message.from_user.id, "Вы это слово уже использовали, так не честно.",      reply_markup=keyboard)
                else:
                    if msg[0].lower() != game_parameters_by_id[message.from_user.id].latest_letter:
                        buttons = ["Счет", "Сдаюсь"]
                        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                        keyboard.add(*buttons)
                        await bot.send_message(message.from_user.id, 'Это не буква ' + game_parameters_by_id[
                            message.from_user.id].latest_letter + ', давайте другое или сдавайтесь.',      reply_markup=keyboard)  # само слово-то надо отправить
                    else:
                        # ищем последнюю букву
                        ll = lastletter_user(msg)  # ищем первую последнюю букву на которую нужно слово
                        if ll == -1:
                            buttons = ["Счет", "Сдаюсь"]
                            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                            keyboard.add(*buttons)
                            await bot.send_message(message.from_user.id,     "Я знаю только слова на русском... Давайте какое-нибудь другое слово.",   reply_markup=keyboard)
                        # берем себе, генерим свое, поехали
                        else:
                            if (msg not in [en.lower() for en in   game_parameters_by_id[message.from_user.id].extra_names_learned]) and (  msg not in g_vocab):  # используем тут, не из него берем то хоть на пользу пойдет, чтоб не каждый раз переделывать список, который по определению никогда не меняется
                                game_parameters_by_id[message.from_user.id].extra_names_learned.append(message.text)
                                game_parameters_by_id[message.from_user.id].leftover_names.append(message.text)
                                game_parameters_by_id[message.from_user.id].user_names.append(msg)
                            ll_names = [gn for gn in game_parameters_by_id[message.from_user.id].leftover_names if
                                        gn[0].lower() == msg[ll]]  # выбираем из своих по первой букве
                            if len(ll_names) == 0:  # больше не знает слов на нужную букву
                                game_parameters_by_id[message.from_user.id].g_score[  0] += 1  # бот не смог найти слово - выиграл пользователь
                                await bot.send_message(message.from_user.id,   "Я не знаю больше слов на букву '" + msg[ll] + "'. Вы выиграли!")
                                await bot.send_message(message.from_user.id, "Текущий счет: " + game_parameters_by_id[ message.from_user.id].curr_score())
                                await bot.send_message(message.from_user.id,     "Если захотите еще поиграть, введите /start")
                                await Botstates.st_start.set()
                            else:  # еще есть неиспользованные слова на нужную букву
                                k = random.randint(0,len(  ll_names)-1)  # random first word выбираем с нужной первой буквой как последняя у присланного
                                wk = ll_names[k]
                                game_parameters_by_id[message.from_user.id].leftover_names.remove(wk)
                                ll = lastletter_bot(wk.lower())
                                game_parameters_by_id[message.from_user.id].latest_letter = wk[ll]

                                buttons = ["Счет", "Сдаюсь"]
                                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                                keyboard.add(*buttons)
                                await bot.send_message(message.from_user.id, wk, reply_markup=keyboard)
                                await Botstates.st_word_for_letter.set()
            else:
                buttons = ["Счет", "Сдаюсь"]
                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                keyboard.add(*buttons)
                await bot.send_message(message.from_user.id,  "Я практически уверен, что это не может быть приемлемым словом. Давайте что-нибудь другое придумайте.",    reply_markup=keyboard)  # и ждем опять
        else:
            buttons = ["Счет", "Сдаюсь"]
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.add(*buttons)
            await bot.send_message(message.from_user.id, "Не молчите, в молчании нет букв", reply_markup=keyboard)


@dp.message_handler(content_types=types.ContentType.ANY, state='*')
async def unknown_message(message: types.Message):
    await bot.send_message(message.from_user.id, "Что-то я запутался... так мы играем или нет?")


executor.start_polling(dp)
