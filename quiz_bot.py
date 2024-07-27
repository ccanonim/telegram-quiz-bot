
import random
import openai
from pyrogram import Client, filters
from pyrogram.types import Message
from fuzzywuzzy import fuzz
import os

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

app = Client("quiz_bot",
             api_id=API_ID,
             api_hash=API_HASH,
             bot_token=BOT_TOKEN)

current_question = 0
selected_questions = []
correct_answers = {}
players = []

def generate_question():
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Bana bir Türkçe bilgi yarışması sorusu ve cevabı ver."}
        ]
    )
    question_data = response.choices[0].message['content'].strip().split("\n")
    question = question_data[0].replace("Soru: ", "").strip()
    correct_answer = question_data[1].replace("Cevap: ", "").strip()
    return {'question': question, 'correct_answer': correct_answer}

def fetch_questions():
    questions = [generate_question() for _ in range(30)]
    return questions

def get_hint(answer):
    hint_length = max(1, len(answer) // 3)
    return answer[:hint_length] + '*' * (len(answer) - hint_length)

@app.on_message(filters.command("start_game") & filters.group)
async def start_game(client, message):
    global current_question, selected_questions, correct_answers, players
    selected_questions = fetch_questions()
    current_question = 0
    correct_answers = {}
    players = []

    await message.reply("🎉 Oyun başladı! İlk soru geliyor...")
    await ask_question(client, message.chat.id)

async def ask_question(client, chat_id):
    global current_question, selected_questions
    if current_question < len(selected_questions):
        q = selected_questions[current_question]
        question_text = f"Soru {current_question + 1}: {q['question']}\nİpucu: {get_hint(q['correct_answer'])}"
        await client.send_message(chat_id, question_text)
    else:
        await end_game(client, chat_id)

@app.on_message(filters.text & filters.group)
async def check_answer(client, message: Message):
    global current_question, selected_questions, correct_answers, players
    if current_question < len(selected_questions):
        q = selected_questions[current_question]
        player_id = message.from_user.id
        player_name = message.from_user.first_name

        similarity = fuzz.ratio(message.text.lower(), q['correct_answer'].lower())
        if similarity > 80:
            if player_id not in correct_answers:
                correct_answers[player_id] = 0
            correct_answers[player_id] += 1
            await message.reply(f"Tebrikler {player_name}! Doğru cevap 🎉", quote=True)
            current_question += 1
            await ask_question(client, message.chat.id)
        else:
            await message.reply(f"Maalesef {player_name}, yanlış cevap 😔", quote=True)

async def end_game(client, chat_id):
    global correct_answers
    sorted_players = sorted(correct_answers.items(), key=lambda item: item[1], reverse=True)
    winners = sorted_players[:10]

    result_text = "🏆 Oyun Bitti! Kazananlar:\n"
    for i, (player_id, score) in enumerate(winners):
        user = await app.get_users(player_id)
        result_text += f"{i + 1}. {user.first_name} - {score} doğru cevap\n"

    await client.send_message(chat_id, result_text)

    if winners:
        winner_id, _ = winners[0]
        winner = await app.get_users(winner_id)
        await client.send_message(chat_id, f"🎉 Tebrikler {winner.first_name}! 🏆\n")

if __name__ == "__main__":
    print("Bot çalışıyor...")
    app.run()
