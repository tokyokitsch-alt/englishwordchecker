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
if "correct_count" not in st.session_state:
    st.session_state.correct_count = 0
if "shuffle_mode" not in st.session_state:
    st.session_state.shuffle_mode = False

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
        
        # 🟢 改善：正解率と進捗ゲージの計算・表示
        # 解き終わった問題数（現在の問題を含む）
        answered_q = idx + 1 
        
        # 画面上部に綺麗に並べて表示
        col_info1, col_info2, col_info3 = st.columns(3)
        with col_info1:
            st.metric(label="📊 進捗", value=f"{idx + 1} / {total_words} 問")
        with col_info2:
            st.metric(label="🎯 正解数", value=f"{st.session_state.correct_count} 問")
        with col_info3:
            # まだ1問も判定していないときは0%、それ以外はリアルタイム計算
            # ただし、現在の問題が判定前なら「これまでに解いた問題数」で割る
            divisor = idx if not st.session_state.checked else idx + 1
            if divisor > 0:
                accuracy = int((st.session_state.correct_count / divisor) * 100)
            else:
                accuracy = 100 if st.session_state.correct_count > 0 or idx == 0 else 0
            st.metric(label="💯 現在の正解率", value=f"{accuracy} %")
            
        # 視覚的な進行バー
        st.progress((idx) / total_words)
        
        st.info(f"🤔 この日本語を英語に直すと？: **{current_word['japanese']}**")
        
        # フォームを使って入力と判定を1つのイベントにまとめる
        with st.form(key=f"quiz_form_{st.session_state.round_num}_{idx}", clear_on_submit=False):
            user_ans = st.text_input(
                "英語を小文字で入力してください：", 
                value=st.session_state.user_input,
                disabled=st.session_state.checked
            ).strip().lower()
            
            submit_button = st.form_submit_button(label="🎯 判定する" if not st.session_state.checked else "🔒 判定済み")

        # 判定ボタンが押されたときの処理
        if submit_button and not st.session_state.checked:
            if user_ans == "":
                st.warning("文字を入力してください。")
            else:
                st.session_state.user_input = user_ans
                st.session_state.checked = True
                
                # 🟢 追加：ここで正解数を判定してカウント
                correct_ans = current_word['english'].strip().lower()
                if user_ans == correct_ans:
                    st.session_state.correct_count += 1
                st.rerun()
        
        # 判定後の表示と「次の問題」ボタン
        if st.session_state.checked:
            correct_ans = current_word['english'].strip().lower()
            
            if st.session_state.user_input == correct_ans:
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
            except Exception:
                pass
            
            with st.form(key=f"next_form_{idx}"):
                next_button = st.form_submit_button(label="➡️ 次の問題へ (Enter)")
                if next_button:
                    st.session_state.current_index += 1
                    st.session_state.checked = False
                    st.session_state.user_input = ""
                    st.rerun()
                
    else:
        # 🟢 リトライ（周回）に入るときの処理も修正（正解数をリセット）
        if st.session_state.wrong_words:
            # 最終的なその週の正解率を表示
            final_accuracy = int((st.session_state.correct_count / total_words) * 100)
            st.warning(f"📝 第 {st.session_state.round_num} 週目が終了！ 正解率: {final_accuracy}%")
            st.write(f"間違えた単語が {len(st.session_state.wrong_words)} 問あります。覚えるまでもう一度チャレンジしよう！")
            
            if st.button("🔄 間違った単語だけで再挑戦！"):
                next_words = list(st.session_state.wrong_words)
                if st.session_state.shuffle_mode:
                    random.shuffle(next_words)
                    
                st.session_state.word_list = next_words
                st.session_state.wrong_words = []
                st.session_state.current_index = 0
                st.session_state.correct_count = 0  # 🟢 次の周回のために正解数をリセット
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
                st.session_state.correct_count = 0  # 🟢 リセット
                st.session_state.round_num = 1
                st.session_state.checked = False
                st.session_state.user_input = ""
                st.rerun()

