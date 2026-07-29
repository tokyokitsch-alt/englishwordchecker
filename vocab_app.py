import streamlit as st
import os
import json
import io
from google import genai
from PIL import Image
from gtts import gTTS

st.title("📝 英単語タイピングゲーム")
st.write("英単語のイメージをアップすると、タイピングがはじまります。日本語の意味を見て、正しい英単語をタイピングしよう！")

# 1. APIキーの設定（クラウドのSecretsから自動で読み込む）
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    # 念のため、お家でのテスト用に手動入力欄も残しておきます
    with st.sidebar:
        api_key = st.text_input("Gemini API Key", type="password")

# 2. アプリの状態管理（セッション状態の初期化）
if "word_list" not in st.session_state:
    st.session_state.word_list = []
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "wrong_words" not in st.session_state:
    st.session_state.wrong_words = []
if "checked" not in st.session_state:
    st.session_state.checked = False
if "user_input" not in st.session_state:
    st.session_state.user_input = ""
if "round_num" not in st.session_state:
    st.session_state.round_num = 1

# 3. 単語リスト画像のアップロード
uploaded_file = st.file_uploader("紙の単語リストの画像をアップロードしてください", type=["jpg", "jpeg", "png"])

if uploaded_file and not st.session_state.word_list:
    image = Image.open(uploaded_file)
    st.image(image, caption="アップロードされた画像", use_container_width=True)
    
    if st.button("✨ 単語リストを読み込む"):
        if not api_key:
            st.error("APIキーを入力してください。")
        else:
            with st.spinner("AIが単語を解析しています..."):
                try:
                    client = genai.Client(api_key=api_key)
                    
                    prompt = """
                    この画像から英単語と日本語の意味をすべて抜き出し、以下のJSONフォーマットのみで出力してください。余計な挨拶や説明は一切不要です。
                    英単語はすべて半角の小文字に統一してください。
                    [
                        {"english": "apple", "japanese": "りんご"},
                        {"english": "banana", "japanese": "バナナ"}
                    ]
                    """
                    
                    response = client.models.generate_content(
                        model='gemini-3.5-flash',
                        contents=[image, prompt]
                    )
                    
                    clean_text = response.text.replace("```json", "").replace("```", "").strip()
                    st.session_state.word_list = json.loads(clean_text)
                    st.session_state.current_index = 0
                    st.session_state.wrong_words = []
                    st.session_state.checked = False
                    st.session_state.user_input = ""
                    st.session_state.round_num = 1
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"読み込みエラー: {e}")

# 4. タイピングクイズ画面
if st.session_state.word_list:
    total_words = len(st.session_state.word_list)
    idx = st.session_state.current_index
    
    if idx < total_words:
        current_word = st.session_state.word_list[idx]
        
        st.subheader(f"🔥 チャレンジ第 {st.session_state.round_num} 週目")
        st.write(f"問題 {idx + 1} / {total_words}")
        st.info(f"🤔 この日本語を英語に直すと？: **{current_word['japanese']}**")
        
        # タイピング入力欄
        user_ans = st.text_input(
            "英語を小文字で入力してください：", 
            key=f"input_{st.session_state.round_num}_{idx}", 
            value=st.session_state.user_input
        ).strip().lower()
        
        if not st.session_state.checked:
            if st.button("🎯 判定する") or user_ans:
                if user_ans == "":
                    st.warning("文字を入力してください。")
                else:
                    st.session_state.user_input = user_ans
                    st.session_state.checked = True
                    st.rerun()
        else:
            correct_ans = current_word['english'].strip().lower()
            
            if st.session_state.user_input == correct_ans:
                # 🌟 正解時に星マークを表示
                st.success(f"🎉 正解！ ⭐⭐⭐ 【 {current_word['english']} 】 ⭐⭐⭐")
            else:
                st.error(f"❌ 残念！ 正解は 【 {current_word['english']} 】 でした。")
                if current_word not in st.session_state.wrong_words:
                    st.session_state.wrong_words.append(current_word)
            
            # 音声読み上げ
            try:
                tts = gTTS(text=current_word['english'], lang='en')
                sound_file = io.BytesIO()
                tts.write_to_fp(sound_file)
                sound_file.seek(0)
                st.audio(sound_file, format="audio/mp3", autoplay=True)
            except Exception as e:
                pass
            
            if st.button("➡️ 次の問題へ"):
                st.session_state.current_index += 1
                st.session_state.checked = False
                st.session_state.user_input = ""
                st.rerun()
                
    else:
        if st.session_state.wrong_words:
            st.warning(f"📝 第 {st.session_state.round_num} 週目が終了！ 間違えた単語が {len(st.session_state.wrong_words)} 問あります。")
            st.write("覚えるまでもう一度チャレンジしよう！")
            
            if st.button("🔄 間違えた単語だけで再挑戦！"):
                st.session_state.word_list = list(st.session_state.wrong_words)
                st.session_state.wrong_words = []
                st.session_state.current_index = 0
                st.session_state.round_num += 1
                st.session_state.checked = False
                st.session_state.user_input = ""
                st.rerun()
        else:
            st.balloons()
            st.subheader("🎉 全問正解！完璧にマスターしました！お疲れ様でした！")
            
            if st.button("🔄 もう一度新しい紙からやる"):
                st.session_state.word_list = []
                st.session_state.wrong_words = []
                st.session_state.current_index = 0
                st.session_state.round_num = 1
                st.session_state.checked = False
                st.session_state.user_input = ""
                st.rerun()
