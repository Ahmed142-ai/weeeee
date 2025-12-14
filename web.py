#<------------- IMPORTING REQUIRED LIBRARIES --------------->
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi import FastAPI, Request, Form
from pydantic import BaseModel
from supabase import create_client
import uuid
from groq import Groq
import re
import json
from fastapi.middleware.cors import CORSMiddleware

#<----------------- DATABASE SETUP ----------------->
url = "https://owaounuiwbdfsohnrqfu.supabase.co"
key = """eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im93YW91bnVpd2JkZnNvaG5ycWZ1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUwMDk2MDQsImV4cCI6MjA4MDU4NTYwNH0.TSg0Ny7UiHWs-xIIn2eIv2JUN8j7_NLjejR9YunKKtU"""
db = create_client(url,key)

#<------------ FASTAPI SETUP --------------->
app = FastAPI()

origins = [
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "*"  
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#<----------- Pydantic model لاستقبال JSON ----------->
class TextRequest(BaseModel):
    text: str

#<----------- ADDING USER TO DATABASE ----------->
@app.post("/sign_up")
def add_user(
    username:str,
    user_governrate:str,
    user_email: str,
):
    id = str(uuid.uuid4())
    db.table("users").insert(
        {
            "username":username,
            "governrate":user_governrate,
            "email":user_email,
        }
    ).execute()
    return {"message": f"{username} مرحبا"}

#<------------ CHECK USER IF LOGGED IN ------------>
@app.post("/login")
async def check_log_in(username:str, email:str):
    user = db.table("users")\
             .select("*")\
             .eq("username", username)\
             .eq("email", email)\
             .execute()
    if user.data:
        return {"message": "تم تسجيل الدخول بنجاح", "user": user.data}
    else:
        return {"message": "اسم المستخدم أو البريد الاكتروني غير صحيح"}

#<------------ CHECK RESPONSE ENDPOINT ------------>
@app.post("/check_response")
def check_response(request: TextRequest):
    text = request.text
    apiKey = "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"
    client = Groq(api_key=apiKey)

    prompt = f"""
أنت مساعد ذكاء اصطناعي خبير.
قيم النص التالي من حيث المصداقية:
{text}

أرجوك ارجعلي JSON فقط فيه ثلاث حقول:
1. credibility_score: نسبة من 0 إلى 100
2. sources: قائمة المصادر
3. reason:  سبب لنسبة المصداقية مع الشرح المفصل باللغة العربية بالكامل

مهم جداً: لا تكتب أي نص إضافي خارج ال JSON.
"""

    try:
        chat = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )
    except Exception as e:
        return {"error": f"حدث خطأ مع Groq: {str(e)}"}

    raw_text = chat.choices[0].message.content

    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if not match:
        return {"error": "Groq لم يرجع JSON صالح"}

    try:
        data = json.loads(match.group())
    except json.JSONDecodeError:
        return {"error": "تعذر تحويل النص إلى JSON"}

    return data
