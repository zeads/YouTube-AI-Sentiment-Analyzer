import os
from dotenv import load_dotenv

import google.generativeai as genai
from googleapiclient.discovery import build
import json

import requests


load_dotenv()

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
VIDEO_ID = os.environ.get("VIDEO_ID")


# WEBHOOK_URL = os.environ.get("WEBHOOK_URL_TEST")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL_PROD")


# ==========================================
# FUNGSI 1: MENGAMBIL KOMENTAR YOUTUBE
# ==========================================
def get_youtube_comments(video_id, api_key):
    print(f"[*] Mengambil komentar dari video: {video_id}...")
    youtube = build('youtube', 'v3', developerKey=api_key)
    
    try:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=5, # Kita batasi 5 untuk testing awal
            textFormat="plainText"
        )
        response = request.execute()

        comments = []
        for item in response['items']:
            text = item['snippet']['topLevelComment']['snippet']['textDisplay']
            comments.append(text)
        return comments
    except Exception as e:
        print(f"[!] Error YouTube API: {e}")
        return []

# ==========================================
# FUNGSI 2: ANALISIS SENTIMEN DENGAN GEMINI
# ==========================================
def analyze_sentiment(comment_text, gemini_key):
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel('gemini-1.5-flash') # Versi cepat & efisien
    
    prompt = f"""
    Tugas: Analisis sentimen dari komentar YouTube berikut.
    Komentar: "{comment_text}"
    
    Instruksi: Berikan jawaban HANYA dalam format JSON mentah tanpa markdown:
    {{"sentimen": "POSITIF/NEGATIF/NETRAL", "skor": 1-10, "alasan": "singkat dalam 5 kata"}}
    """
    
    try:
        response = model.generate_content(prompt)
        # Membersihkan output jika AI memberikan format markdown ```json
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except Exception as e:
        return {"error": str(e)}

# ==========================================
# ALUR UTAMA (ORCHESTRATION)
# ==========================================
if __name__ == "__main__":
    # 1. Ambil Data
    raw_comments = get_youtube_comments(VIDEO_ID, YOUTUBE_API_KEY)
    
    if raw_comments:
        results = []
        print(f"[*] Berhasil mengambil {len(raw_comments)} komentar.")
        print("-" * 30)
        
        # 2. Proses dengan AI
        for i, comment in enumerate(raw_comments, 1):
            print(f"[{i}] Menganalisis: {comment[:50]}...")
            analysis = analyze_sentiment(comment, GEMINI_API_KEY)
            
            # Gabungkan komentar asli dengan hasil analisis
            entry = {
                "komentar": comment,
                "analisis": analysis
            }
            results.append(entry)
        
        # 3. Tampilkan Hasil Akhir (Atau simpan ke file)
        print("-" * 30)
        print(json.dumps(results, indent=4))
    else:
        print("[!] Tidak ada komentar yang ditemukan.")
        


if __name__ == "__main__":
    raw_comments = get_youtube_comments(VIDEO_ID, YOUTUBE_API_KEY)
    
    if raw_comments:
        print(f"[*] Memulai pengiriman data ke Google Sheets via Webhook...")
        
        for comment in raw_comments:
            # 1. Analisis dengan AI
            analysis = analyze_sentiment(comment, GEMINI_API_KEY)
            
            # 2. Siapkan data untuk dikirim
            payload = {
                "komentar": comment,
                "sentimen": analysis.get("sentimen"),
                "skor": analysis.get("skor"),
                "alasan": analysis.get("alasan")
            }
            
            # 3. Kirim ke Webhook
            try:
                response = requests.post(WEBHOOK_URL, json=payload)
                if response.status_code == 200:
                    print(f"[OK] Berhasil mengirim: {analysis.get('sentimen')}")
                else:
                    print(f"[!] Gagal mengirim. Status: {response.status_code}")
            except Exception as e:
                print(f"[!] Error saat mengirim data: {e}")

        print("-" * 30)
        print("[FINISH] Semua data telah diproses.")