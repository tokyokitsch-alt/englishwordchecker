import streamlit as st
import cv2
import numpy as np
from PIL import Image

# ページの設定とタイトル
st.set_page_config(page_title="Print Resetter", page_icon="📄", layout="centered")
st.title("📄 Print Resetter")
st.write("解き終わったプリントから手書き（色ペン）の文字を消して、A4印刷用に整えます。")

# 1. 画像のアップロード
uploaded_file = st.file_uploader("プリントの画像をアップロードしてください", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    # 画像の読み込み
    image = Image.open(uploaded_file)
    img_array = np.array(image)
    
    # 画面を2列に分けて、ビフォーアフターを見やすくする
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("元の画像")
        st.image(image, use_container_width=True)
    
    # 2. 消したい色の選択
    pen_color = st.selectbox("消したいペンの色を選んでください", ["赤ペン（赤・ピンク・オレンジ）", "青ペン（青・水色）"])
    
    # 3. 画像処理（色抽出して白で塗りつぶす）
    # RGBからHSV（色を扱いやすい空間）に変換
    hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
    
    if "赤ペン" in pen_color:
        # 赤色の範囲（色相の端と端に分かれるため2つの範囲を結合）
        lower1 = np.array([0, 50, 50])
        upper1 = np.array([10, 255, 255])
        lower2 = np.array([170, 50, 50])
        upper2 = np.array([180, 255, 255])
        mask1 = cv2.inRange(hsv, lower1, upper1)
        mask2 = cv2.inRange(hsv, lower2, upper2)
        mask = mask1 + mask2
    else:
        # 青色の範囲
        lower_blue = np.array([90, 50, 50])
        upper_blue = np.array([130, 255, 255])
        mask = cv2.inRange(hsv, lower_blue, upper_blue)
        
    # 検知した色（ペン書き）の部分を「純粋な白」に置き換える
    result_img = img_array.copy()
    result_img[mask > 0] = [255, 255, 255]
    
    # 4. A4印刷用にコントラストを調整（白黒をはっきりさせる）
    gray = cv2.cvtColor(result_img, cv2.COLOR_RGB2GRAY)
    
    # 少しぼかして裏写りやノイズを軽減
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    
    # 適応的二値化：周囲の明るさに合わせて文字をくっきり浮かび上がらせる
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 21, 10
    )
    
    with col2:
        st.subheader("リセット後")
        st.image(thresh, use_container_width=True, channels="GRAY")
    
    # 5. ダウンロードボタンの配置
    # PIL画像に変換して一時保存
    result_pil = Image.fromarray(thresh)
    result_pil.save("reprint_ready.png")
    
    with open("reprint_ready.png", "rb") as file:
        st.download_button(
            label="✨ A4印刷用画像をダウンロード",
            data=file,
            file_name="print_resetter_output.png",
            mime="image/png"
        )
