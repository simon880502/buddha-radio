import streamlit as st
import pandas as pd
from datetime import date
import requests # 新增這個套件
import io

st.set_page_config(page_title="佛法小故事電台", page_icon="🙏", layout="centered")

# --- 核心功能：後端直接抓取音檔 (解決 0:00 問題的終極解法) ---
@st.cache_data(show_spinner=False) # 加入快取，避免每次重整都重新下載
def download_audio_content(url):
    try:
        # 檢查 URL 是否為空
        if pd.isna(url) or str(url).strip() == "":
            return None

        url = str(url).strip()
        file_id = ""
        # 1. 解析 ID
        if "id=" in url:
            file_id = url.split("id=")[1].split("&")[0]
        elif "/file/d/" in url:
            file_id = url.split("/file/d/")[1].split("/")[0]

        if not file_id:
            return None

        # 2. 構建下載連結
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

        # 3. Python 後端下載 (繞過瀏覽器限制)
        response = requests.get(download_url, timeout=10)
        if response.status_code == 200:
            return response.content
        return None
    except Exception as e:
        st.warning(f"下載音檔時發生錯誤：{str(e)}")
        return None

# --- 資料處理 ---
sheet_id = "1ldalRSuQRjXdeG2EXKIiZafKd9LxG6yqKDtXZpF7UX8"
csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

@st.cache_data(ttl=60)
def load_data():
    try:
        data = pd.read_csv(csv_url)
        
        # 日期強力修正：直接切掉時間部分，只留日期
        def safe_parse_date(val):
            try:
                if pd.isna(val): return None
                # "2026/2/5 下午 8:55:36" -> 遇到空白就切斷 -> "2026/2/5"
                date_part = str(val).split(' ')[0] 
                return pd.to_datetime(date_part).date()
            except:
                return None

        col_title = "標題："
        col_file = "錄音檔案上傳"
        col_ts = "時間戳記"
        col_date_manual = "日期"

        data['processed_ts'] = data[col_ts].apply(safe_parse_date)
        data['processed_manual'] = data[col_date_manual].apply(safe_parse_date)
        data['display_date'] = data['processed_manual'].fillna(data['processed_ts'])
        
        return data, col_title, col_file
    except Exception as e:
        st.error(f"連線錯誤：{e}")
        return None, None, None

# --- 介面 ---
st.title("🙏 佛法小故事電台")

df, col_title, col_file = load_data()

if df is not None:
    today = date.today()
    st.info(f"📅 今天的日期是：{today}")
    
    # 1. 今日精選
    today_stories = df[df['display_date'] == today]
    
    if not today_stories.empty:
        st.subheader("✨ 今日精選故事")
        for _, row in today_stories.iterrows():
            st.markdown(f"### {row[col_title]}")
            
            # 使用「下載模式」播放
            with st.spinner('正在載入音檔...'):
                audio_bytes = download_audio_content(row[col_file])
                if audio_bytes:
                    # 這裡明確指定 format='audio/mp4' (對應 m4a)
                    st.audio(audio_bytes, format='audio/mp4')
                else:
                    st.error("音檔讀取失敗，請確認 Google Drive 權限。")

    else:
        st.warning("今天還沒上傳新故事。")

    # 2. 隨機播放
    st.divider()
    if st.button("🔀 隨機聽一段"):
        # 過濾掉標題為空的記錄
        valid_stories = df[df[col_title].notna() & (df[col_title] != "")]

        if not valid_stories.empty:
            random_story = valid_stories.sample(n=1).iloc[0]
            st.success(f"📖 推薦題目：**{random_story[col_title]}**")

            with st.spinner('正在載入音檔...'):
                audio_bytes_rand = download_audio_content(random_story[col_file])
                if audio_bytes_rand:
                    st.audio(audio_bytes_rand, format='audio/mp4')
                else:
                    st.error(f"音檔讀取失敗。連結：{random_story[col_file]}")
        else:
            st.warning("沒有可用的故事。")

    # 3. 歷史回顧
    st.divider()
    st.subheader("📜 歷史回顧")
    all_dates = sorted(df['display_date'].dropna().unique(), reverse=True)
    
    if all_dates:
        sel_date = st.selectbox("選擇日期", all_dates)
        hist_stories = df[df['display_date'] == sel_date]
        for _, row in hist_stories.iterrows():
            st.write(f"🔹 **{row[col_title]}**")
            # 歷史區塊我們只用連結顯示，避免一次下載太多卡住
            # 如果需要也可以改成 download_audio_content
            st.audio(download_audio_content(row[col_file]), format='audio/mp4')

else:
    st.error("無法讀取資料表。")
