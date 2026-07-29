import streamlit as st
import os
import json
import io
import tempfile
import urllib.request
import numpy as np
from google import genai
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

st.title("🚗 車で流せる！英単語動画メーカー & タイピング")
st.write("紙の単語帳画像から、ドライブ中に車内で流せる英語学習動画を自動作成します。")

# 1. APIキーの設定
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    with st.sidebar:
        api_key = st.text_input("Gemini API Key", type="password")

# 2. セッション状態の初期化
if "word_list" not in st.session_state:
    st.session_state.word_list = []

# --------------------------------------------------
# 車内学習向け：動画カード画像生成関数
# --------------------------------------------------
def create_drive_card(japanese, main_text, is_answer=False):
    """車内の画面で見やすいハイコントラスト・超大型文字のカード画像を生成"""
    video_size = (1280, 720) # 16:9 (車のナビ・モニターに最適)
    
    # 背景と文字色（くっきり見やすいコントラスト）
    bg_color = (255, 255, 255) if not is_answer else (240, 249, 255) # 正解時はうっすら水色
    ja_color = (15, 23, 42)       # 濃いネイビー（日本語）
    en_color = (225, 29, 72) if is_answer else (100, 116, 139) # 正解英単語は赤みのある色で強調

    base_img = Image.new('RGB', video_size, color=bg_color)
    draw = ImageDraw.Draw(base_img)

    # 日本語対応フォントの自動ダウンロード（環境依存を解決）
    font_path = "NotoSansJP-Bold.ttf"
    if not os.path.exists(font_path):
        try:
            # Google Fontsから日本語フォントをダウンロード
            url = "https://github.com"
            urllib.request.urlretrieve(url, font_path)
        except Exception:
            pass

    # フォント設定（視認性を高めるため超大きめ）
    try:
        if os.path.exists(font_path):
            font_ja = ImageFont.truetype(font_path, 75)
            font_en = ImageFont.truetype(font_path, 110)
        else:
            # 万が一ダウンロードに失敗した場合はシステムのフォントを試す
            font_ja = ImageFont.truetype("msgothic.ttc", 75)
            font_en = ImageFont.truetype("arial.ttf", 110)
    except IOError:
        font_ja = ImageFont.load_default()
        font_en = ImageFont.load_default()

    # 1. 日本語の意味（画面上部）
    bbox_ja = draw.textbbox((0, 0), japanese, font=font_ja)
    ja_w = bbox_ja[2] - bbox_ja[0]
    draw.text(((video_size[0] - ja_w) // 2, 130), japanese, fill=ja_color, font=font_ja)

    # 区切り線
    draw.line([(200, 270), (1080, 270)], fill=(203, 213, 225), width=4)

    # 2. 英単語または伏字（画面下部・極大表示）
    bbox_en = draw.textbbox((0, 0), main_text, font=font_en)
    en_w = bbox_en[2] - bbox_en[0]
    draw.text(((video_size[0] - en_w) // 2, 380), main_text, fill=en_color, font=font_en)

    return np.array(base_img)

# --------------------------------------------------
# 車内学習向け：動画生成処理
# --------------------------------------------------
def generate_drive_video(word_list):
    """単語リストから車内学習用MP4動画を生成"""
    clips = []
    temp_files = []

    for idx, item in enumerate(word_list):
        english = item["english"].strip().lower()
        japanese = item["japanese"].strip()

        # 音声1: 日本語の読み上げ (例: 「りんご」)
        tts_ja = gTTS(text=japanese, lang='ja')
        f_ja = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts_ja.save(f_ja.name)
        temp_files.append(f_ja.name)
        audio_ja = AudioFileClip(f_ja.name)

        # 音声2: 英語の読み上げ (例: "apple")
        tts_en = gTTS(text=english, lang='en', slow=False)
        f_en = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts_en.save(f_en.name)
        temp_files.append(f_en.name)
        audio_en = AudioFileClip(f_en.name)

        # --- 1. 問題フェーズ ---
        # 日本語を声で流しつつ、画面には「日本語」と「伏字(_ _ _)」を表示（約3秒）
        mask_text = " ".join(["_"] * len(english))
        q_img = create_drive_card(japanese, mask_text, is_answer=False)
        q_duration = max(3.0, audio_ja.duration + 1.5) # 日本語音声＋少し考える時間
        q_clip = ImageClip(q_img).set_duration(q_duration).set_audio(audio_ja)

        # --- 2. 正解フェーズ ---
        # 英語の発音を流しつつ、画面に大きな「英単語」を表示（約3秒）
        spaced_word = " ".join(list(english))
        a_img = create_drive_card(japanese, spaced_word, is_answer=True)
        a_duration = max(3.0, audio_en.duration + 1.0)
        a_clip = ImageClip(a_img).set_duration(a_duration).set_audio(audio_en)

        clips.extend([q_clip, a_clip])

    # 1本の動画に結合
    final_clip = concatenate_videoclips(clips, method="compose")
    output_video = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    final_clip.write_videofile(output_video.name, fps=24, codec="libx264", audio_codec="aac")

    # 一時ファイルの削除
    for tf in temp_files:
        if os.path.exists(tf):
            os.remove(tf)

    return output_video.name

# 3. 画像アップロード & AI解析
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
                    この画像から英単語と日本語の意味をすべて抜き出し、以下のJSONフォーマットのみで出力してください。
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
                    st.rerun()
                except Exception as e:
                    st.error(f"読み込みエラー: {e}")

# 4. 単語読み込み後の機能表示
if st.session_state.word_list:
    st.success(f"単語リスト（全 {len(st.session_state.word_list)} 問）を読み込みました！")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("🚗 車内用動画をつくる")
        st.write("耳で聴いて覚えられる音声付き動画（MP4）を生成します。")
        if st.button("🎥 ドライブ動画を生成する"):
            with st.spinner("車内用動画を作成中...（1〜2分かかります）"):
                try:
                    video_path = generate_drive_video(st.session_state.word_list)
                    with open(video_path, "rb") as f:
                        st.download_button(
                            label="💾 動画（MP4）をダウンロード",
                            data=f,
                            file_name="drive_english_lesson.mp4",
                            mime="video/mp4"
                        )
                    st.success("作成完了！スマホやUSBメモリに入れて車内で流せます。")
                except Exception as e:
                    st.error(f"動画作成エラー: {e}")

    with col2:
        st.header("📋 読み込んだ単語一覧")
        st.json(st.session_state.word_list)
