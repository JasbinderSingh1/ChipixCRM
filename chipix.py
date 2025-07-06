import streamlit as st
from supabase import create_client
from fpdf import FPDF
from io import BytesIO
from datetime import datetime
import pytz
import time

# ──────────────────────────────────────────────────────────
# 1. SUPABASE SETUP (from secrets)
# ──────────────────────────────────────────────────────────
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
ADMIN_USERNAME = st.secrets["ADMIN_USERNAME"]
ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ──────────────────────────────────────────────────────────
# 2. ADMIN LOGIN
# ──────────────────────────────────────────────────────────
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

# ──────────────────────────────────────────────────────────
# 3. MAIN DASHBOARD
# ──────────────────────────────────────────────────────────
st.markdown("<h1 style='font-family: Arial; color: #1363DF;'>Chipix CRM - Customer, Sales & Service Management</h1>", unsafe_allow_html=True)

# IST Live Clock
ist = pytz.timezone('Asia/Kolkata')
clock_placeholder = st.empty()

# Live updating clock every second using Streamlit Autorefresh
with st.empty():
    while True:
        clock_placeholder.markdown(f"### 🕒 Current IST Time: {datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S')}")
        time.sleep(1)
        st.rerun()

# ──────────────────────────────────────────────────────────
# 4. ADD NEW ENTRY
# ──────────────────────────────────────────────────────────
if 'entry_data' not in st.session_state:
    st.session_state.entry_data = {
        'name': '',
        'phone': '',
        'product': '',
        'price': 0.0,
        'warranty': '',
        'item': '',
        'issue': '',
        'status': ''
    }

with st.form("new_entry_form", clear_on_submit=True):
    st.subheader("➕ Add New Entry")
    st.session_state.entry_data['name'] = st.text_input("Customer Name")
    st.session_state.entry_data['phone'] = st.text_input("Phone Number")
    entry_type = st.radio("Entry Type", ["Purchase", "Service"], horizontal=True)

    def validate_inputs():
        if not st.session_state.entry_data['name'].replace(" ", "").isalpha():
            st.error("❌ Name must contain only letters.")
            return False
        if not st.session_state.entry_data['phone'].isdigit() or len(st.session_state.entry_data['phone']) != 10:
            st.error("❌ Phone number must be exactly 10 digits.")
            return False
        return True

    details = {}
    if entry_type == "Purchase":
        st.markdown("### 🛒 Purchase Details")
        st.session_state.entry_data['product'] = st.text_input("Product Name")
        st.session_state.entry_data['price'] = st.number_input("Amount Paid (₹)", min_value=0.0, format="%.2f")
        st.session_state.entry_data['warranty'] = st.selectbox("Warranty Period", ["No Warranty", "1 Month", "3 Months", "6 Months", "1 Year", "2 Years"])
        details = {
            "product": st.session_state.entry_data['product'],
            "price": st.session_state.entry_data['price'],
            "warranty": st.session_state.entry_data['warranty']
        }
    else:
        st.markdown("### 🛠️ Service Details")
        st.session_state.entry_data['item'] = st.text_input("Electronic Item")
        st.session_state.entry_data['issue'] = st.text_area("Issue Description")
        st.session_state.entry_data['status'] = st.selectbox("Initial Status", ["Pending", "In Progress", "Completed"])
        details = {
            "item": st.session_state.entry_data['item'],
            "issue": st.session_state.entry_data['issue'],
            "status": st.session_state.entry_data['status']
        }

    submitted = st.form_submit_button("Submit Entry")

    if submitted:
        if validate_inputs() and all(details.values()):
            ist_now = datetime.now(ist).isoformat()
            entry = {
                "name": st.session_state.entry_data['name'],
                "phone": st.session_state.entry_data['phone'],
                "entry_type": entry_type,
                "timestamp": ist_now,
                **details
            }
            response = supabase.table("chipix_customers").insert(entry).execute()

            if hasattr(response, "data") and response.data:
                st.success(f"✅ {entry_type} entry for {entry['name']} recorded at {ist_now}.")
                st.session_state.entry_data = {k: '' if isinstance(v, str) else 0.0 for k, v in st.session_state.entry_data.items()}
                st.rerun()
            else:
                error_msg = getattr(getattr(response, "error", None), "message", "Unknown error")
                st.error(f"❌ Failed to add entry. Error: {error_msg}")
        else:
            st.error("❌ Please fill all required fields.")

# ──────────────────────────────────────────────────────────
# 5. SEARCH & HISTORY
# ──────────────────────────────────────────────────────────
with st.expander("🔍 Search Past Records"):
    query = st.text_input("Search by Name or Phone")
    if query:
        result = supabase.table("chipix_customers").select("*").or_(f"phone.ilike.%{query}%,name.ilike.%{query}%").order("timestamp", desc=True).execute()
        records = result.data if hasattr(result, "data") else []

        if records:
            for record in records:
                st.markdown(f"### 🎫 Record for {record['name']}")
                for k, v in record.items():
                    st.write(f"{k}: {v}")

                def generate_invoice(entry):
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", size=12)
                    pdf.cell(200, 10, txt="Chipix Invoice", ln=True, align="C")
                    pdf.cell(200, 10, txt="Generated by Chipix CRM", ln=True, align="C")
                    pdf.ln(10)
                    for key, val in entry.items():
                        safe_val = str(val).encode("latin-1", "replace").decode("latin-1")
                        pdf.cell(200, 10, txt=f"{key}: {safe_val}", ln=True)
                    buffer = BytesIO()
                    pdf_output = pdf.output(dest='S').encode('latin-1')
                    buffer.write(pdf_output)
                    buffer.seek(0)
                    return buffer

                pdf_buffer = generate_invoice(record)
                st.download_button("📥 Download Invoice PDF", data=pdf_buffer, file_name=f"{record['name']}_invoice.pdf")
        else:
            st.warning("No matching record found.")
