import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import json
import time
import datetime
import threading
import os
import pytz
import requests
from bs4 import BeautifulSoup

TOKEN = '8777717354:AAG9q7hdlQ0ViEeONoE45WGyWy2zq-PI0Z4'
ADMIN_ID = 6454550864
#RealTime project salah
FIREBASE_URL = "https://salah-64eaa-default-rtdb.firebaseio.com/users/"
bot = telebot.TeleBot(TOKEN, parse_mode='HTML')
IRAQ_TZ = pytz.timezone('Asia/Baghdad')

user_states = {}

# ---- دوال Firebase (Realtime Database API) ----
def get_user_data(user_id):
    try:
        res = requests.get(f"{FIREBASE_URL}{user_id}.json", timeout=5)
        if res.status_code == 200 and res.json():
            return res.json()
    except Exception as e:
        print("Firebase Error Get:", e)
    return None

def save_user_data(user_id, data):
    try:
        requests.put(f"{FIREBASE_URL}{user_id}.json", json=data, timeout=5)
    except Exception as e:
        print("Firebase Error Save:", e)

def get_all_users():
    try:
        res = requests.get(f"{FIREBASE_URL}.json", timeout=5)
        if res.status_code == 200 and res.json():
            return res.json()
    except Exception as e:
        print("Firebase Error Get All:", e)
    return {}

def init_user(user_id):
    uid = str(user_id)
    data = get_user_data(uid)
    
    if not data:
        data = {
            "prayers": {
                "الصبح": 0,
                "الظهر والعصر": 0,
                "المغرب والعشاء": 0
            },
            "notes": {
                "الصبح": "",
                "الظهر والعصر": "",
                "المغرب والعشاء": ""
            },
            "night_reminder": False
        }
        save_user_data(uid, data)
        return data
    
    # التأكد من صحة الهيكل وتحديثه تلقائياً
    updated = False
    if "prayers" not in data:
        data["prayers"] = {"الصبح": 0, "الظهر والعصر": 0, "المغرب والعشاء": 0}
        updated = True
    if "notes" not in data:
        data["notes"] = {"الصبح": "", "الظهر والعصر": "", "المغرب والعشاء": ""}
        updated = True
    if "night_reminder" not in data:
        data["night_reminder"] = False
        updated = True
        
    if updated:
        save_user_data(uid, data)
        
    return data

# ---- جلب التاريخ الهجري ----
from bs4 import BeautifulSoup
from hijri_converter import convert

def get_sistani_hijri_date():
    try:
        url = "https://www.sistani.org/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            text = soup.get_text()
            if "١٤٤" in text or "144" in text:
                for line in text.split('\n'):
                    if ("هـ" in line or "AH" in line) and any(m in line for m in ["صفر", "ربيع", "رجب", "شعبان", "رمضان", "محرم", "شوال", "ذو", "جمادى"]):
                        return line.strip()
    except:
        pass
    
    # fallback: حساب التاريخ الهجري الحالي
    today = datetime.datetime.now(IRAQ_TZ).date()
    hijri_date = convert.Gregorian(today.year, today.month, today.day).to_hijri()
    return f"{hijri_date.day} {hijri_date.month_name()} {hijri_date.year} هـ (محسوب محلياً)"

# مثال تشغيل
print(get_sistani_hijri_date())


# ---- واجهة اللوحة الرئيسية ----
def build_main_dashboard(user_id):
    user_data = init_user(user_id)
    now_iraq = datetime.datetime.now(IRAQ_TZ)
    
    gregorian_date = now_iraq.strftime("%Y/%m/%d")
    days_ar = {"Monday": "الأثنين", "Tuesday": "الثلاثاء", "Wednesday": "الأربعاء", "Thursday": "الخميس", "Friday": "الجمعة", "Saturday": "السبت", "Sunday": "الأحد"}
    day_ar = days_ar.get(now_iraq.strftime("%A"), now_iraq.strftime("%A"))
    hijri_date = get_sistani_hijri_date()

    header_text = (
        f"مرحبا بك في هذا البوت ✨\n "
        f"هو بوت مجرد تذكير لك لقضاء صلاواتك الفائتة.\n"
        f"تم استخدم <b>Firbase</b> لضمان عدم فقدان بياناتك .\n"
        f"قم بتسجيل صلاواتك بالاسفل مع الملاحظات .\n \n"
    )
    data_text = (
        f"<b>🗓 التاريخ اليوم:</b>\n"
        f"<blockquote>"
        f"• اليوم: <b>{day_ar}</b>\n"
        f"• الميلادي: <code>{gregorian_date}</code>\n"
        f"• الهجري : <b>{hijri_date}</b>"
        f"</blockquote>\n"
    )
    
    times_text = (
        f"<b>⏰ أوقات التذكير اليومية الثابتة:</b>\n"
        f"<blockquote>"
        f"• صلاة الصبح: <code>03:40 ص</code>\n"
        f"• صلاة الظهر والعصر: <code>12:00 م</code>\n"
        f"• صلاة المغرب والعشاء: <code>07:00 م</code>\n"
        f"• صلاة الليل: <code>11:15 م</code> \n هذه هي الاوقات التي ستصلك التذكيرات اذا كان لديك تذكير معين \n تم استخدام الاوقات بالتقريب مع مدينة بابل وليس اوقات الصلاة الاصلية بل انها مجرد تذكير قبل موعد الصلاة الحقيقي بـ5-10 دقائق ."
        f"</blockquote>\n"
    )

    prayers = user_data.get("prayers", {})
    notes = user_data.get("notes", {})
    
    qada_text = "<b>📋 إحصائيات الصلوات القضاء:</b>\n<blockquote>"
    has_qada = False
    for p, count in prayers.items():
        if count > 0:
            note_str = f"\n <i>(ملاحظة: {notes.get(p)})</i> \n" if notes.get(p) else ""
            qada_text += f"• {p}: <b>{count}</b> صلاة{note_str}\n"
            has_qada = True
            
    if not has_qada:
        qada_text += "لا توجد عليك صلوات قضاء مسجلة حالياً ✨\n"
    qada_text += "</blockquote>\n"

    night_status = "مفعل 🔔" if user_data.get("night_reminder", False) else "معطل 🔕"
    night_text = f"<b>🌙 تذكير صلاة الليل:</b> <code>{night_status}</code>\n\n"

    full_text = header_text + data_text + times_text + qada_text + night_text + "اضغط على الأزرار أدناه لإضافة صلاة قضاء فوراً أو للتحكم بالإعدادات:"

    markup = InlineKeyboardMarkup()
    
    row_add = [
        InlineKeyboardButton("➕ الصبح", callback_data="add_الصبح"),
        InlineKeyboardButton("➕ الظهر والعصر", callback_data="add_الظهر والعصر"),
        InlineKeyboardButton("➕ المغرب والعشاء", callback_data="add_المغرب والعشاء")
    ]
    row_ctrl = [
        InlineKeyboardButton("⚙️ تعديل وملاحظات", callback_data="manage_qada"),
        InlineKeyboardButton("🌙 صلاة الليل", callback_data="night_menu"),
        InlineKeyboardButton("Dev 👩‍💻", url="https://t.me/alii_index")
    ]
    
    markup.row(*row_add)
    markup.row(*row_ctrl)
    
    if user_id == ADMIN_ID:
        markup.row(InlineKeyboardButton("⚙️ اختبار الإشعارات (للأدمن)", callback_data="test_admin"))

    return full_text, markup

# ---- نظام التذكير (الثريد) ----
def reminder_thread():
    last_sent_min = None
    while True:
        now = datetime.datetime.now(IRAQ_TZ).strftime("%H:%M")
        if now != last_sent_min:
            all_users = get_all_users()
            schedule = {
                "03:40": "الصبح",
                "16:03": "الظهر والعصر",
                "19:00": "المغرب والعشاء"
            }
            
            # تذكير صلاة القضاء
            if now in schedule:
                p = schedule[now]
                for uid, udata in all_users.items():
                    count = udata.get("prayers", {}).get(p, 0)
                    if count > 0:
                        note = udata.get("notes", {}).get(p, "")
                        note_text = f"\n📝 ملاحظتك: {note}" if note else ""
                        msg = f"🔔 <b>تذكير صلاة قضاء:</b> {p}\n<blockquote>العدد المطلوب الحالي: {count}{note_text}</blockquote> \n عندما تصلي هذه الصلاة القضاء اضغط على الزر بالاسفل لكي يتم احتساب الصلاة ."
                        markup = InlineKeyboardMarkup()
                        markup.add(InlineKeyboardButton("صليتها ✅", callback_data=f"done_{p}"))
                        try: bot.send_message(uid, msg, reply_markup=markup)
                        except: pass

            # تذكير صلاة الليل
            if now == "23:15":
                for uid, udata in all_users.items():
                    if udata.get("night_reminder", False):
                        try:
                            bot.send_message(uid, "✨ <b>حان الآن وقت صلاة الليل (11:15 PM) الوقت الان كصورة تقريبية لمواقيت العراق تأخر 5 دقايق لتجنب الشك. \nاذا لم تتعلم صلاة الليل هذه طريقتها : \n https://t.me/XX28Z/633\n</b>\n<blockquote>اللهم وفقنا لقيام الليل وتقبل منا ومنكم صالح الأعمال.</blockquote>")
                        except: pass
                
            last_sent_min = now
        time.sleep(10)

# ---- الأوامر والردود ----
@bot.message_handler(commands=['start'])
def start_cmd(message):
    init_user(message.from_user.id)
    text, markup = build_main_dashboard(message.from_user.id)
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: str(m.from_user.id) in user_states)
def handle_notes_input(message):
    uid = str(message.from_user.id)
    prayer = user_states[uid]
    data = init_user(uid)
    
    data["notes"][prayer] = message.text.strip()
    save_user_data(uid, data)
    
    del user_states[uid]
    bot.send_message(message.chat.id, f"✅ تم حفظ الملاحظة لصلاة <b>{prayer}</b> بنجاح!")
    show_prayer_card(message.chat.id, message.from_user.id, prayer, is_new_msg=True)

def show_prayer_card(chat_id, user_id, prayer, message_id=None, is_new_msg=False):
    data = init_user(user_id)
    count = data["prayers"].get(prayer, 0)
    note = data["notes"].get(prayer, "")
    note_str = note if note else "لا توجد ملاحظة"
    
    msg = (
        f"<b>⚙️ إدارة قضاء صلاة: {prayer}</b>\n\n"
        f"<blockquote>"
        f"• العدد الحالي: <b>{count}</b>\n"
        f"• الملاحظة: <b>{note_str}</b>"
        f"</blockquote>\n"
        f"اختر إجراءً للتعديل:"
    )
    
    markup = InlineKeyboardMarkup()
    row1 = [
        InlineKeyboardButton("➕ إضافة قضاء", callback_data=f"p_add_{prayer}"),
        InlineKeyboardButton("➖ مسح قضاء", callback_data=f"p_sub_{prayer}")
    ]
    row2 = [InlineKeyboardButton("🗑 مسح الصلاة بالكامل", callback_data=f"p_clear_{prayer}")]
    row3 = [InlineKeyboardButton("📝 إضافة / تعديل ملاحظة", callback_data=f"p_note_{prayer}")]
    row4 = [
        InlineKeyboardButton("🔙 رجوع للصلوات", callback_data="manage_qada"),
        InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")
    ]
    
    markup.row(*row1)
    markup.row(*row2)
    markup.row(*row3)
    markup.row(*row4)
    
    if is_new_msg:
        bot.send_message(chat_id, msg, reply_markup=markup)
    else:
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    uid = str(call.from_user.id)
    user_id = call.from_user.id
    
    # إضافة صلاة سريعة
    if call.data.startswith('add_'):
        prayer = call.data.replace('add_', '')
        data = init_user(user_id)
        data["prayers"][prayer] += 1
        save_user_data(uid, data)
        
        bot.answer_callback_query(call.id, f"تمت إضافة 1 لصلاة {prayer}")
        text, markup = build_main_dashboard(user_id)
        try: bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=markup)
        except: pass

    # القائمة الرئيسية
    elif call.data == "main_menu":
        text, markup = build_main_dashboard(user_id)
        try: bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=markup)
        except: pass

    # قائمة إدارة الصلوات
    elif call.data == "manage_qada":
        data = init_user(user_id)
        msg = "<b>✏️ اختر الصلاة لتعديل إحصائياتها أو إضافة ملاحظة:</b>"
        markup = InlineKeyboardMarkup()
        
        for p in ["الصبح", "الظهر والعصر", "المغرب والعشاء"]:
            c = data["prayers"].get(p, 0)
            markup.row(InlineKeyboardButton(f"{p} (المطلوب: {c})", callback_data=f"select_p_{p}"))
            
        markup.row(InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=msg, reply_markup=markup)

    elif call.data.startswith("select_p_"):
        prayer = call.data.replace("select_p_", "")
        show_prayer_card(call.message.chat.id, user_id, prayer, call.message.message_id)

    elif call.data.startswith("p_add_"):
        prayer = call.data.replace("p_add_", "")
        data = init_user(user_id)
        data["prayers"][prayer] += 1
        save_user_data(uid, data)
        bot.answer_callback_query(call.id, "+1 تمت الإضافة")
        show_prayer_card(call.message.chat.id, user_id, prayer, call.message.message_id)

    elif call.data.startswith("p_sub_"):
        prayer = call.data.replace("p_sub_", "")
        data = init_user(user_id)
        if data["prayers"][prayer] > 0:
            data["prayers"][prayer] -= 1
            save_user_data(uid, data)
            bot.answer_callback_query(call.id, "-1 تم الخصم")
        else:
            bot.answer_callback_query(call.id, "العدد بالفعل 0!", show_alert=True)
        show_prayer_card(call.message.chat.id, user_id, prayer, call.message.message_id)

    elif call.data.startswith("p_clear_"):
        prayer = call.data.replace("p_clear_", "")
        data = init_user(user_id)
        data["prayers"][prayer] = 0
        data["notes"][prayer] = ""
        save_user_data(uid, data)
        bot.answer_callback_query(call.id, "تم تصفير الصلاة ومسح الملاحظة", show_alert=True)
        show_prayer_card(call.message.chat.id, user_id, prayer, call.message.message_id)

    elif call.data.startswith("p_note_"):
        prayer = call.data.replace("p_note_", "")
        user_states[uid] = prayer
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"📝 <b>أرسل الآن الملاحظة</b> التي تريد حفظها لصلاة <b>{prayer}</b>:")

    elif call.data == "night_menu":
        data = init_user(user_id)
        is_active = data.get("night_reminder", False)
        
        msg = (
            f"<b>🌙 صلاة الليل</b>\n\n"
            f"<blockquote>صلاة الليل صلاة مستحبة، وموعد التذكير الثابت هو الساعة <b>11:15 مساءً</b>.</blockquote>\n\n"
            f"اذا لم تتعلم لها اضغط على زر (طريقة الصلاة) \n"
            f"الحالة الحالية للتذكير: <b>{'مفعل 🔔' if is_active else 'معطل 🔕'}</b>"
        )
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🔕 إلغاء التذكير" if is_active else "🔔 تأكيد تفعيل التذكير", callback_data="toggle_night"))
        markup.row(InlineKeyboardButton("طريقة الصلاة", url="https://t.me/XX28Z/633"))
        markup.row(InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=msg, reply_markup=markup)

    elif call.data == "toggle_night":
        data = init_user(user_id)
        data["night_reminder"] = not data.get("night_reminder", False)
        save_user_data(uid, data)
        
        status_msg = "تم تفعيل تذكير صلاة الليل بنجاح! 🔔" if data["night_reminder"] else "تم إلغاء تذكير صلاة الليل. 🔕"
        bot.answer_callback_query(call.id, status_msg, show_alert=True)
        msg = f"<b>🌙 صلاة الليل</b>\n\n<blockquote>{status_msg}</blockquote>"
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🏠 رجوع للقائمة الرئيسية", callback_data="main_menu"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=msg, reply_markup=markup)

    elif call.data == "test_admin" and user_id == ADMIN_ID:
        msg_qada = "🔔 <b>(اختبار) تذكير صلاة قضاء:</b> الظهر والعصر\n<blockquote>العدد المطلوب الحالي: 1\n📝 ملاحظتك: اختبار</blockquote>"
        markup_qada = InlineKeyboardMarkup()
        markup_qada.add(InlineKeyboardButton("صليتها ✅", callback_data="done_الظهر والعصر"))
        bot.send_message(ADMIN_ID, msg_qada, reply_markup=markup_qada)
        bot.send_message(ADMIN_ID, "✨ <b>(اختبار) حان الآن وقت صلاة الليل (11:15 PM).</b>\n<blockquote>اللهم وفقنا لقيام الليل وتقبل منا ومنكم صالح الأعمال.</blockquote>")
        bot.answer_callback_query(call.id, "تم إرسال رسائل الاختبار بنجاح!")

    elif call.data.startswith('done_'):
        prayer = call.data.replace('done_', '')
        data = init_user(user_id)
        
        if data["prayers"].get(prayer, 0) > 0:
            data["prayers"][prayer] -= 1
            remains = data["prayers"][prayer]
            save_user_data(uid, data)
            
            if remains > 0:
                alert_text = f"تقبل الله طاعتك! ✅\nتم خصم صلاة، المتبقي عليك من {prayer} هو: ({remains}) صلاة."
            else:
                alert_text = f"عاشت ايدك! تقبل الله طاعتك 🌸\nأكملت جميع الصلوات المطلوبة منك لصلاة {prayer}."
                
            bot.answer_callback_query(call.id, alert_text, show_alert=True)
            try: bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            except: pass
        else:
            bot.answer_callback_query(call.id, "لا توجد صلاة مطلوبة مسجلة لهذا النوع حالياً.", show_alert=True)

if __name__ == '__main__':
    threading.Thread(target=reminder_thread, daemon=True).start()
    print("البوت يعمل ومربوط بـ Firebase بنجاح...")
    bot.infinity_polling()
