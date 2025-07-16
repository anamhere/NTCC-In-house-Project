import streamlit as st
from datetime import datetime
from PIL import Image
import dateparser
import random
import pandas as pd
import plotly.express as px
from db import db, collection
from scheduler import start_scheduler
from ocr import extract_expiry_date
from utils import get_expiry_status
from fpdf import FPDF
import re
from bson.objectid import ObjectId
import copy
from io import BytesIO

# ============ THEME INIT ============ #
if "theme" not in st.session_state:
    st.session_state["theme"] = "dark"

def set_theme(new_theme):
    st.session_state["theme"] = new_theme
    st.rerun()

# ============ PAGE CONFIG ============ #
st.set_page_config(page_title="🌟 Smart AI Expiry Tracker", page_icon="🛍", layout="wide")

# ============ CUSTOM CSS ============ #
dark_styles = """
body {
    background: linear-gradient(135deg, #141e30, #243b55);
    font-family: 'Segoe UI', sans-serif;
}
"""

light_styles = """
body {
    background: linear-gradient(135deg, #fdfbfb, #ebedee);
    font-family: 'Segoe UI', sans-serif;
}
"""

common_styles = """
h1 {
    font-size: 3rem;
    font-weight: bold;
    text-align: center;
    background: linear-gradient(90deg, #a18cd1, #fbc2eb);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: glow 2s ease-in-out infinite alternate;
}
@keyframes glow {
    from { text-shadow: 0 0 10px #a18cd1; }
    to { text-shadow: 0 0 20px #fbc2eb; }
}
.tip, .quote {
    text-align: center;
    font-style: italic;
    font-size: 1.1rem;
    color: #ffe3ff;
    margin-top: 1rem;
}
.login-header {
    font-size: 2.7rem;
    text-align: center;
    font-weight: bold;
    background: linear-gradient(90deg, #a18cd1, #fbc2eb);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.login-subheader {
    text-align: center;
    font-style: italic;
    font-size: 1.2rem;
    margin-top: -10px;
    color: #fce3ff;
}
.sidebar-content {
    font-size: 1rem;
    color: #ffe3ff;
    padding-bottom: 8px;
    border-bottom: 1px dashed #fff;
    margin-bottom: 10px;
    font-style: italic;
}
.badge {
    font-size: 14px;
    font-weight: bold;
    padding: 10px;
    border-radius: 10px;
    background: linear-gradient(90deg, #a18cd1, #fbc2eb);
    color: white;
    margin-bottom: 1rem;
    text-align: center;
    word-break: break-word;
}
.link-style {
    color: #fbc2eb;
    text-decoration: underline;
    font-size: 1rem;
    text-align: center;
    display: block;
    margin-top: 0.5rem;
    cursor: pointer;
}
.link-style:hover {
    color: white;
}
.logout-button button {
    background: linear-gradient(90deg, #ff758c, #ff7eb3);
    color: white;
    border: none;
    font-size: 16px;
    font-weight: bold;
    border-radius: 20px;
    padding: 10px 20px;
    width: 100%;
}
.logout-button button:hover {
    box-shadow: 0 4px 15px rgba(255, 150, 200, 0.5);
    transform: scale(1.02);
}
"""

theme_css = dark_styles if st.session_state["theme"] == "dark" else light_styles
st.markdown(f"<style>{theme_css + common_styles}</style>", unsafe_allow_html=True)

# ============ SIDEBAR ============ #
with st.sidebar:
    email_display = st.session_state.get("user_email", "Guest") or "Guest"
    st.markdown(f"<div class='badge'>👤 Logged in as:<br>{email_display}</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class='sidebar-content'>💬 “Let food be thy medicine and medicine be thy food.” – Hippocrates</div>
    <div class='sidebar-content'>🌈 “Smart shelves, no waste!”</div>
    <div class='sidebar-content'>🧠 AI keeps your pantry clean and lean!</div>
    """, unsafe_allow_html=True)

    if email_display != "Guest":
        user_products = list(collection.find({"user_email": email_display, "is_deleted": {"$ne": True}}))
        now = datetime.now()
        expired = sum(get_expiry_status(p["expiry"]) == "Expired" for p in user_products)
        expiring = sum(get_expiry_status(p["expiry"]) == "Expiring Soon" for p in user_products)
        fresh = sum(get_expiry_status(p["expiry"]) == "Fresh" for p in user_products)
        st.markdown(f"""
        <div class='sidebar-content'>❗ Expired Items: <b>{expired}</b></div>
        <div class='sidebar-content'>⚡ Expiring Soon: <b>{expiring}</b></div>
        <div class='sidebar-content'>🌱 Fresh Items: <b>{fresh}</b></div>
        """, unsafe_allow_html=True)

    theme_choice = st.radio("🌙☀ Theme:", ["dark", "light"], index=0 if st.session_state["theme"] == "dark" else 1)
    if theme_choice != st.session_state["theme"]:
        set_theme(theme_choice)
# ============ AUTH UTILITY ============ #

def login_user(email, password):
    user = db["users"].find_one({"email": email})
    return bool(user and user["password"] == password)

def register_user(email, password):
    if db["users"].find_one({"email": email}):
        return False
    db["users"].insert_one({"email": email, "password": password})
    return True

def assess_password_strength(password):
    if len(password) < 6:
        return "Weak: too short"
    if not re.search(r"[A-Z]", password):
        return "Fair: add uppercase"
    if not re.search(r"[0-9]", password):
        return "Fair: add number"
    if not re.search(r"[^A-Za-z0-9]", password):
        return "Fair: add special character"
    return "Strong ✅"

# ============ SESSION INIT ============ #
if "user_email" not in st.session_state:
    st.session_state["user_email"] = None
if "show_login" not in st.session_state:
    st.session_state["show_login"] = True
if "last_deleted_item" not in st.session_state:
    st.session_state["last_deleted_item"] = None

# ============ LOGIN / SIGNUP UI ============ #
if st.session_state["user_email"] is None:
    st.markdown("<div class='login-header'>🌟 Smart Expiry Tracker</div>", unsafe_allow_html=True)
    st.markdown("<div class='login-subheader'>“Organize your pantry with AI – Smart, Fast, Magical! 🪄”</div>", unsafe_allow_html=True)

    if st.session_state["show_login"]:
        with st.form("login_form"):
            st.markdown("<h3 style='text-align:center;'>👤 Sign In</h3>", unsafe_allow_html=True)
            email = st.text_input("Email:", key="login_email")
            password = st.text_input("Password:", type="password", key="login_pw")
            submit = st.form_submit_button("🚀 Sign In")
            if submit:
                if login_user(email, password):
                    st.session_state["user_email"] = email
                    st.success(f"✅ Welcome back, {email}!")
                    st.rerun()
                else:
                    st.error("❌ Incorrect email or password.")
            st.markdown("<div class='link-style' onclick='document.forms[\"signup_form\"].submit();'>Don't have an account? <u>Sign up here</u></div>", unsafe_allow_html=True)
    else:
        with st.form("signup_form"):
            st.markdown("<h3 style='text-align:center;'>📝 Create an Account</h3>", unsafe_allow_html=True)
            reg_email = st.text_input("Email:", key="register_email")
            reg_pw = st.text_input("Password:", type="password", key="register_pw")
            strength = assess_password_strength(reg_pw)
            st.markdown(f"<div class='sidebar-content'>🔐 Password Strength: <i>{strength}</i></div>", unsafe_allow_html=True)
            submit = st.form_submit_button("🌟 Sign Up Now")
            if submit:
                if strength != "Strong ✅":
                    st.warning("⚠ Please use a stronger password.")
                else:
                    if register_user(reg_email, reg_pw):
                        st.success("🎉 Registration successful! You can now sign in.")
                        st.session_state["show_login"] = True
                        st.rerun()
                    else:
                        st.error("❌ Email already registered.")
            st.markdown("<div class='link-style'>Already have an account? <u>Click to sign in</u></div>", unsafe_allow_html=True)

    # Toggle Login/Signup state if clicked
    if st.button("🔁 Switch to " + ("Sign Up" if st.session_state["show_login"] else "Sign In"), use_container_width=True):
        st.session_state["show_login"] = not st.session_state["show_login"]
        st.rerun()

    st.stop()
# ============ LOGGED IN DASHBOARD HEADER ============ #

main_col1, main_col2 = st.columns([5, 1])
with main_col2:
    with st.container():
        st.markdown("<div class='logout-button'>", unsafe_allow_html=True)
        if st.button("🔓 Log Out", use_container_width=True):
            st.session_state["user_email"] = None
            st.session_state["show_login"] = True
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# Main headline
st.markdown("<h1>🛍 Smart AI Grocery Expiry Tracker</h1>", unsafe_allow_html=True)
st.markdown("<div class='login-subheader'>“Track today, save tomorrow. Make AI your pantry pal.” 🧠</div>", unsafe_allow_html=True)

# ============ SCHEDULER INIT ============ #
if "scheduler_started" not in st.session_state:
    start_scheduler()
    st.session_state["scheduler_started"] = True
    st.success("✅ Notification scheduler started.")

# ============ METRICS ============ #
user_email = st.session_state["user_email"]
all_products = list(collection.find({"user_email": user_email, "is_deleted": {"$ne": True}}))
now = datetime.now()
expired_count = sum(get_expiry_status(p["expiry"]) == "Expired" for p in all_products)
soon_count = sum(get_expiry_status(p["expiry"]) == "Expiring Soon" for p in all_products)
fresh_count = sum(get_expiry_status(p["expiry"]) == "Fresh" for p in all_products)

c1, c2, c3 = st.columns(3)
c1.metric("⏳ Expired Items", expired_count)
c2.metric("⚡ Expiring Soon (3d)", soon_count)
c3.metric("🌱 Fresh Items", fresh_count)

# ============ DAILY TIPS & QUOTES ============ #
tips = [
    "🥕 Store carrots in water for longer freshness.",
    "🥛 Keep milk in the coldest part of the fridge.",
    "🍞 Freeze bread slices to make them last longer.",
    "🥦 Wrap broccoli in foil to keep it crisp.",
    "🍓 Rinse berries with vinegar water to preserve them.",
    "🧀 Keep cheese in parchment, not plastic!"
]
quotes = [
    "“Fresh is best” 🥬",
    "“Waste not, want not” 🌍",
    "“Good food is worth preserving” 🍱",
    "“Smart tracking saves smart money” 💰",
    "“Track today, save tomorrow” 📆"
]

st.markdown(f"<div class='tip'>💡 Tip of the Day: <i>{random.choice(tips)}</i></div>", unsafe_allow_html=True)
st.markdown(f"<div class='quote'>🌟 Quote of the Day: <i>{random.choice(quotes)}</i></div>", unsafe_allow_html=True)

# ============ NAVIGATION TABS ============ #
tab_products, tab_add, tab_insights, tab_alerts, tab_recycle_bin = st.tabs(
    ["📋 Products", "➕ Add Item", "📊 Insights", "⚡ Alerts", "♻ Recycle Bin"]
)
# ============ PRODUCTS TAB ============ #
with tab_products:
    st.markdown("<h2>📋 Products List</h2>", unsafe_allow_html=True)
    search_term = st.text_input("🔍 Search by Product Name").strip().lower()
    filter_option = st.selectbox("📂 Filter by:", ["All Items", "Expiring This Week", "Expired Only"])
    show_products = st.checkbox("👀 Show Products List?", value=True)

    if show_products:
        products = []
        for p in collection.find({"user_email": user_email, "is_deleted": {"$ne": True}}):
            expiry = p["expiry"]
            if isinstance(expiry, str):
                expiry = dateparser.parse(expiry)
            p["expiry_dt"] = expiry
            p["days_left"] = (expiry - now).days
            products.append(p)

        if filter_option == "Expiring This Week":
            products = [p for p in products if 0 <= p["days_left"] <= 7]
        elif filter_option == "Expired Only":
            products = [p for p in products if p["days_left"] < 0]

        if search_term:
            products = [p for p in products if search_term in p["name"].lower()]

        if products:
            export_df = pd.DataFrame([{
                "Name": p["name"],
                "Expiry Date": p["expiry_dt"].strftime("%Y-%m-%d"),
                "Days Left": p["days_left"],
                "Status": get_expiry_status(p["expiry_dt"])
            } for p in products])

            # CSV Export
            st.download_button("💾 Export as CSV",
                               data=export_df.to_csv(index=False).encode("utf-8"),
                               file_name="grocery_products.csv",
                               mime="text/csv")

            # Excel Export
            excel_buffer = BytesIO()
            export_df.to_excel(excel_buffer, index=False)
            excel_buffer.seek(0)
            st.download_button("📊 Export as Excel",
                               data=excel_buffer,
                               file_name="grocery_products.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            # PDF Export
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="Grocery Product List", ln=True, align='C')
            pdf.ln(10)
            for _, row in export_df.iterrows():
                line = f"{row['Name']} | {row['Expiry Date']} | {row['Days Left']} days | {row['Status']}"
                pdf.multi_cell(0, 10, txt=line)

            pdf_buffer = BytesIO()
            pdf_output = pdf.output(dest='S').encode('latin-1')
            pdf_buffer.write(pdf_output)
            pdf_buffer.seek(0)
            st.download_button("📄 Export as PDF",
                               data=pdf_buffer,
                               file_name="grocery_products.pdf",
                               mime="application/pdf")

            # Display products
            for p in sorted(products, key=lambda x: x["expiry_dt"]):
                days = p["days_left"]
                exp = p["expiry_dt"].strftime("%Y-%m-%d")
                status = get_expiry_status(p["expiry_dt"])
                emoji = "❌" if status == "Expired" else ("⚠" if status == "Expiring Soon" else "✅")
                pid = str(p["_id"])

                col_item, col_edit, col_del = st.columns([4, 1, 1])
                with col_item:
                    st.markdown(
                        f"<div style='font-size:1.1rem;'>{emoji} <b>{p['name']}</b> — Expires in {abs(days)} day(s) ({exp}) [{status}]</div>",
                        unsafe_allow_html=True)
                with col_edit:
                    if st.button("🖋️", key=f"edit_{pid}"):
                        new_name = st.text_input(f"Edit name for {p['name']}:", key=f"new_name_{pid}")
                        new_expiry = st.date_input(f"Edit expiry for {p['name']}:", value=p["expiry_dt"],
                                                   key=f"edit_expiry_{pid}")
                        if st.button("✅ Save", key=f"save_{pid}"):
                            collection.update_one({"_id": p["_id"]},
                                                  {"$set": {
                                                      "name": new_name,
                                                      "expiry": datetime(new_expiry.year, new_expiry.month,
                                                                         new_expiry.day)
                                                  }})
                            st.success(f"✅ Updated {new_name}")
                            st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"delete_{pid}"):
                        st.session_state["last_deleted_item"] = copy.deepcopy(p)
                        collection.update_one({"_id": p["_id"]}, {"$set": {"is_deleted": True}})
                        st.warning(f"🗑 Deleted {p['name']}.")

            # Undo
            if st.session_state["last_deleted_item"]:
                undo = st.session_state["last_deleted_item"]
                if st.button(f"↩️ Undo Delete for {undo['name']}", key=f"undo_{str(undo['_id'])}"):
                    collection.update_one({"_id": undo['_id']}, {"$set": {"is_deleted": False}})
                    st.success(f"✅ Restored {undo['name']}")
                    st.session_state["last_deleted_item"] = None
                    st.rerun()
        else:
            st.warning("😔 No products match your criteria.")
# ============ ADD ITEM TAB ============ #
with tab_add:
    st.markdown("<h2>➕ Add Item Manually</h2>", unsafe_allow_html=True)
    with st.form("manual_entry_form"):
        name = st.text_input("Product Name")
        expiry_date = st.date_input("Expiry Date")
        submitted = st.form_submit_button("✅ Add Product")
        if submitted and name:
            expiry_dt = datetime(expiry_date.year, expiry_date.month, expiry_date.day)
            collection.insert_one({
                "user_email": user_email,
                "name": name,
                "expiry": expiry_dt,
                "is_deleted": False
            })
            st.success(f"✅ Added {name}, expiring on {expiry_dt.strftime('%Y-%m-%d')}.")

    st.markdown("<h2>📷 Add Item via Image (OCR Detection)</h2>", unsafe_allow_html=True)
    uploaded_image = st.file_uploader("Upload an image of the label (JPG, PNG):", type=["jpg", "jpeg", "png"])
    if uploaded_image:
        image = Image.open(uploaded_image)
        st.image(image, caption="Uploaded Image", use_column_width=True)

        detected_date = extract_expiry_date(uploaded_image)
        if detected_date:
            st.success(f"✅ Detected Expiry Date: {detected_date.strftime('%Y-%m-%d')}")
            with st.form("ocr_confirm_form"):
                product_name = st.text_input("Product Name (Enter Manually): ")
                confirm = st.form_submit_button("✅ Add Product from Image")
                if confirm and product_name:
                    collection.insert_one({
                        "user_email": user_email,
                        "name": product_name,
                        "expiry": detected_date,
                        "is_deleted": False
                    })
                    st.success(f"✅ Added {product_name}, expiring on {detected_date.strftime('%Y-%m-%d')}.")
        else:
            st.warning("⚠ No expiry date detected in the image.")

# ============ INSIGHTS TAB ============ #
with tab_insights:
    st.markdown("<h2>📊 Expiry Insights</h2>", unsafe_allow_html=True)
    status_counts = {"Fresh": fresh_count, "Expiring Soon": soon_count, "Expired": expired_count}
    fig = px.pie(
        names=list(status_counts.keys()),
        values=list(status_counts.values()),
        title="Product Status Distribution",
        color_discrete_sequence=["#00C851", "#ffbb33", "#ff4444"]
    )
    st.plotly_chart(fig, use_container_width=True)

    timeline_data = []
    for p in all_products:
        if "expiry" in p:
            timeline_data.append({"Product": p["name"], "Expiry Date": p["expiry"]})

    if timeline_data:
        timeline_df = pd.DataFrame(timeline_data).sort_values(by="Expiry Date")
        fig_timeline = px.line(
            timeline_df,
            x="Expiry Date",
            y="Product",
            title="Product Expiry Timeline",
            markers=True,
            color_discrete_sequence=["#764ba2"]
        )
        st.plotly_chart(fig_timeline, use_container_width=True)

# ============ ALERTS TAB ============ #
with tab_alerts:
    st.markdown("<h2>⚡ Alerts</h2>", unsafe_allow_html=True)
    soon_products = [p for p in all_products if get_expiry_status(p["expiry"]) == "Expiring Soon"]
    if soon_products:
        for p in soon_products:
            st.warning(f"⚠ {p['name']} expires on {p['expiry'].strftime('%Y-%m-%d')}. Consider using it soon.")
    else:
        st.success("✅ No expiring soon alerts.")

# ============ RECYCLE BIN TAB ============ #
with tab_recycle_bin:
    st.markdown("<h2>♻ Deleted Items</h2>", unsafe_allow_html=True)
    deleted_products = list(collection.find({"user_email": user_email, "is_deleted": True}))
    if deleted_products:
        for p in deleted_products:
            pid = str(p["_id"])
            col_item, col_restore, col_delete = st.columns([3, 1, 1])
            with col_item:
                st.markdown(f"🗑 {p['name']} - Expired on {p['expiry'].strftime('%Y-%m-%d')}")
            with col_restore:
                if st.button(f"↩️ Restore", key=f"recycle_restore_{pid}"):
                    collection.update_one({"_id": p['_id']}, {"$set": {"is_deleted": False}})
                    st.success(f"✅ Restored {p['name']}")
                    st.rerun()
            with col_delete:
                if st.button(f"❌ Delete", key=f"recycle_delete_{pid}"):
                    collection.delete_one({"_id": p['_id']})
                    st.warning(f"🗑 Permanently deleted {p['name']}.")
                    st.rerun()
    else:
        st.success("🌱 No deleted products found.")
# ============ ENHANCED CSS CONTINUED ============ #
final_custom_css = """
<style>
.logout-button button {
    font-size: 16px !important;
    font-weight: 600 !important;
    color: white !important;
    background: linear-gradient(135deg, #ff416c, #ff4b2b) !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 10px 20px !important;
    transition: all 0.3s ease-in-out !important;
    box-shadow: 0px 4px 15px rgba(255, 99, 132, 0.3) !important;
}
.logout-button button:hover {
    background: linear-gradient(135deg, #ff4b2b, #ff416c) !important;
    transform: scale(1.05) !important;
    box-shadow: 0px 6px 18px rgba(255, 99, 132, 0.5) !important;
}
.tip, .quote {
    margin-top: 1rem;
    text-align: center;
    font-style: italic;
    color: #ffe9f9;
    font-size: 1.2rem;
    font-family: 'Comic Sans MS', cursive, sans-serif;
}
.tip {
    animation: fadeIn 1.5s ease-in;
}
.quote {
    animation: fadeIn 2s ease-in;
}
@keyframes fadeIn {
    from {opacity: 0;}
    to {opacity: 1;}
}
.login-subheader {
    margin-top: 0.2rem;
    font-size: 1.2rem;
    font-style: italic;
    text-align: center;
    color: #dcd0ff;
    font-family: 'Lucida Handwriting', cursive;
    animation: fadeIn 2s ease-in-out;
}
</style>
"""
st.markdown(final_custom_css, unsafe_allow_html=True)

# ============ FOOTER ============ #
st.markdown("""
    <hr style='margin-top: 2rem; border-top: 1px dashed #999;'/>
    <div style="text-align: center; font-size: 1rem; color: #ffe3ff; font-style: italic;">
        🌟 <i>Smart AI Expiry Tracker</i> | “Stay Fresh, Stay Smart!” 🌱<br/>
        Built with ❤ using Streamlit, MongoDB, OCR & AI | © 2025
    </div>
""", unsafe_allow_html=True)