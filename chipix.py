import streamlit as st
from supabase import create_client
from fpdf import FPDF
from io import BytesIO
from datetime import datetime
import pytz

# ─────────────────────────────────────────────────────────────────────
# 1. SUPABASE SETUP (from secrets)
# ─────────────────────────────────────────────────────────────────────
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
ADMIN_USERNAME = st.secrets["ADMIN_USERNAME"]
ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─────────────────────────────────────────────────────────────────────
# 2. ADMIN LOGIN
# ─────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Chipix CRM", layout="wide")

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h1 style='font-family: Arial; color: #1363DF;'>Chipix CRM Login</h1>", unsafe_allow_html=True)
    admin_username = st.text_input("Admin Username")
    admin_password = st.text_input("Admin Password", type="password")

    if admin_username == ADMIN_USERNAME and admin_password == ADMIN_PASSWORD:
        st.session_state.authenticated = True
        st.rerun()
    else:
        st.stop()

# ─────────────────────────────────────────────────────────────────────
# 3. MAIN DASHBOARD
# ─────────────────────────────────────────────────────────────────────
st.markdown("<h1 style='font-family: Arial; color: #1363DF;'>Chipix CRM - Customer, Sales & Service Management</h1>", unsafe_allow_html=True)

# IST Live Clock
ist = pytz.timezone('Asia/Kolkata')
st.markdown(f"### 🕒 Current IST Time: {datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S')}")

# ─────────────────────────────────────────────────────────────────────
# 4. ADD NEW ENTRY
# ─────────────────────────────────────────────────────────────────────
with st.form("new_entry_form"):
    st.subheader("➕ Add New Entry")
    name = st.text_input("Customer Name")
    phone = st.text_input("Phone Number")
    entry_type = st.radio("Entry Type", ["Purchase", "Service"])

    def validate_inputs():
        if not name.replace(" ", "").isalpha():
            st.error("❌ Name must contain only letters.")
            return False
        if not phone.isdigit() or len(phone) != 10:
            st.error("❌ Phone number must be exactly 10 digits.")
            return False
        return True

    details = {}
    if entry_type == "Purchase":
        details['product'] = st.text_input("Product Name")
        details['price'] = st.number_input("Amount Paid (₹)", min_value=0.0, format="%.2f")
        details['warranty'] = st.selectbox("Warranty Period", ["No Warranty", "1 Month", "3 Months", "6 Months", "1 Year", "2 Years"])
    else:
        details['item'] = st.text_input("Electronic Item")
        details['issue'] = st.text_area("Issue Description")
        details['status'] = st.selectbox("Initial Status", ["Pending", "In Progress", "Completed"])

    submitted = st.form_submit_button("Submit Entry")

    if submitted:
        if validate_inputs() and all(details.values()):
            ist_now = datetime.now(ist).isoformat()
            entry = {
                "name": name,
                "phone": phone,
                "entry_type": entry_type,
                "timestamp": ist_now,
                **details
            }
            response = supabase.table("chipix_customers").insert(entry).execute()

            if hasattr(response, "data") and response.data:
                st.success(f"✅ {entry_type} entry for {name} recorded at {ist_now}.")
                st.rerun()
            else:
                error_msg = getattr(getattr(response, "error", None), "message", "Unknown error")
                st.error(f"❌ Failed to add entry. Error: {error_msg}")
        else:
            st.error("❌ Please fill all required fields.")
