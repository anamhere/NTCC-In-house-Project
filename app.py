import streamlit as st
from pymongo import MongoClient
from PIL import Image
import pytesseract
import dateparser
from datetime import datetime, timedelta
import re
import cv2
import numpy as np





# --- Page config ---



st.set_page_config(page_title="AI Grocery Expiry Tracker", page_icon="🧠")

st.title("🧠 AI Grocery Expiry Tracker")
st.subheader("Track your grocery expiry dates easily!")
st.info("You can manually enter grocery items or upload a photo to detect expiry dates. Let’s get started!")






# --- MongoDB Setup ---
client = MongoClient("mongodb+srv://Armanwarraich:Arman4496@groceryexpirytracker.piw9elf.mongodb.net/")
db = client["grocery_db"]
collection = db["products"]




# --- Helper Function ---
def preprocess_image(image):
    img = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 11, 2
    )
    return thresh





# --- Manual Entry ---
st.header("Add Item Manually")
with st.form("manual_entry_form"):
    name = st.text_input("Product Name")
    expiry_date = st.date_input("Expiry Date")
    submitted = st.form_submit_button("Add Product")
    if submitted:
        if name:
            expiry_dt = datetime(year=expiry_date.year, month=expiry_date.month, day=expiry_date.day)
            collection.insert_one({"name": name, "expiry": expiry_dt})
            st.success(f"Added **{name}**, expiring on {expiry_date}")
        else:
            st.error("Please enter a product name")






# --- Image Upload Entry ---
st.header("Add Item via Image")
uploaded_image = st.file_uploader("Upload an image of the product/label (JPG, PNG)", type=["jpg", "jpeg", "png"])

if uploaded_image:
    image = Image.open(uploaded_image)
    st.image(image, caption="Uploaded Image", use_column_width=True)

    img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    custom_config = r'--oem 3 --psm 6'
    extracted_text = pytesseract.image_to_string(thresh, config=custom_config)
    st.text_area("Extracted Text", extracted_text)

    date_matches = re.findall(r'\b(?:\d{1,2}[/-])?(?:[A-Za-z]{3,9}|\d{1,2})[./-]\d{1,4}\b', extracted_text)
    detected_date = None
    for date_str in date_matches:
        parsed = dateparser.parse(date_str, settings={'PREFER_DATES_FROM': 'future'})
        if parsed:
            detected_date = parsed
            break

    if detected_date:
        st.success(f"Detected Expiry Date: {detected_date.strftime('%Y-%m-%d')}")
        with st.form("ocr_confirm_form"):
            product_name = st.text_input("Product Name (enter manually)")
            confirm = st.form_submit_button("Add Product from Image")
            if confirm and product_name:
                collection.insert_one({"name": product_name, "expiry": detected_date})
                st.success(f"Added **{product_name}** expiring on {detected_date.strftime('%Y-%m-%d')}")
    else:
        st.warning("No expiry date detected in the image.")


# --- Upload Size Display ---
current_upload_size = st.get_option("server.maxUploadSize")
st.write(f"Current max upload size: {current_upload_size} MB")











# --- Filters Above Stored Products ---
st.header("Stored Products")

# --- Search & Filter Inputs ---
search_term = st.text_input("🔍 Search by product name").strip().lower()

filter_option = st.selectbox(
    "Filter by:",
    ["All items", "Expiring this week", "Expired only"]
)

# Initialize toggle state
if 'show_products' not in st.session_state:
    st.session_state.show_products = False

# Show / Hide buttons
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("Show Products"):
        st.session_state.show_products = True
with col2:
    if st.button("Hide Products"):
        st.session_state.show_products = False

# Only fetch & display when toggled on
if st.session_state.show_products:
    products = list(collection.find())
    now = datetime.now()

    # Annotate each with days_left
    for p in products:
        expiry = p['expiry']
        if isinstance(expiry, str):
            expiry = dateparser.parse(expiry)
        p['expiry_dt'] = expiry
        p['days_left'] = (expiry - now).days

    # Apply filter_option
    if filter_option == "Expiring this week":
        products = [p for p in products if 0 <= p['days_left'] <= 7]
    elif filter_option == "Expired only":
        products = [p for p in products if p['days_left'] < 0]

    # Apply search_term
    if search_term:
        products = [
            p for p in products
            if search_term in p['name'].lower()
        ]

    if not products:
        st.info("No products match your criteria.")
    else:
        # Sort: expired first (oldest first), then upcoming (soonest first)
        expired   = sorted([p for p in products if p['days_left'] < 0],
                           key=lambda x: x['expiry_dt'])
        upcoming  = sorted([p for p in products if p['days_left'] >= 0],
                           key=lambda x: x['expiry_dt'])

        for p in expired + upcoming:
            days = p['days_left']
            name = p['name']
            exp  = p['expiry_dt'].strftime("%Y-%m-%d")

            colA, colB = st.columns([4, 1])
            with colA:
                if days < 0:
                    st.write(f"**{name}** — expired {abs(days)} day(s) ago ({exp})")
                elif days <= 3:
                    st.markdown(
                        f"<span style='color:red'>**{name}** — expires in {days} day(s) ({exp})</span>",
                        unsafe_allow_html=True
                    )
                else:
                    st.write(f"**{name}** — expires in {days} day(s) ({exp})")
            with colB:
                if st.button("Delete", key=f"del_{p['_id']}"):
                    collection.delete_one({"_id": p["_id"]})
                    st.success(f"Deleted product: {name}")
                    st.experimental_rerun()









