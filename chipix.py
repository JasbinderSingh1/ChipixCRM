import streamlit as st
from supabase import create_client
from fpdf import FPDF
from io import BytesIO
from datetime import datetime
import pytz

# ──────────────────────────────
# 1. Setup
# ──────────────────────────────
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
ADMIN_USERNAME = st.secrets["ADMIN_USERNAME"]
ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Chipix CRM", layout="wide")

# ──────────────────────────────
# 2. Authentication
# ──────────────────────────────
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h1 style='color: #1363DF;'>Chipix CRM Login</h1>", unsafe_allow_html=True)
    admin_username = st.text_input("Admin Username")
    admin_password = st.text_input("Admin Password", type="password")

    if admin_username == ADMIN_USERNAME and admin_password == ADMIN_PASSWORD:
        st.session_state.authenticated = True
        st.rerun()
    else:
        st.stop()

# ──────────────────────────────
# 3. Dashboard Header
# ──────────────────────────────
st.markdown("<h1 style='color: #1363DF;'>Chipix CRM - Customer, Sales & Service Management</h1>", unsafe_allow_html=True)

# Live IST Clock
ist = pytz.timezone('Asia/Kolkata')
current_time = datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"### 🕒 Current IST Time: `{current_time}`")

# ──────────────────────────────
# 4. Add Entry Form
# ──────────────────────────────
with st.form("new_entry_form", clear_on_submit=True):
    st.subheader("➕ Add New Entry")
    name = st.text_input("Customer Name")
    phone = st.text_input("Phone Number")
    entry_type = st.radio("Entry Type", ["Purchase", "Service"], horizontal=True)

    def validate():
        if not name.strip().replace(" ", "").isalpha():
            st.error("Name must contain only letters.")
            return False
        if not phone.isdigit() or len(phone) != 10:
            st.error("Phone number must be 10 digits.")
            return False
        return True

    details = {}
    if entry_type == "Purchase":
        st.markdown("#### 🛒 Purchase Details")
        product = st.text_input("Product Name")
        price = st.number_input("Amount Paid (₹)", min_value=0.0, format="%.2f")
        warranty = st.selectbox("Warranty Period", ["No Warranty", "1 Month", "3 Months", "6 Months", "1 Year", "2 Years"])
        details = {"product": product, "price": price, "warranty": warranty}
    else:
        st.markdown("#### 🛠️ Service Details")
        item = st.text_input("Electronic Item")
        issue = st.text_area("Issue Description")
        status = st.selectbox("Initial Status", ["Pending", "In Progress", "Completed"])
        details = {"item": item, "issue": issue, "status": status}

    submitted = st.form_submit_button("Submit Entry")

    if submitted:
        if validate() and all(details.values()):
            timestamp = datetime.now(ist).isoformat()
            entry = {"name": name, "phone": phone, "entry_type": entry_type, "timestamp": timestamp, **details}
            response = supabase.table("chipix_customers").insert(entry).execute()

            if hasattr(response, "data") and response.data:
                st.success(f"✅ {entry_type} entry for {name} recorded at `{timestamp}`.")
            else:
                error = getattr(getattr(response, "error", None), "message", "Unknown error")
                st.error(f"❌ Entry failed: {error}")
        else:
            st.warning("⚠️ Please fill all fields correctly.")

# ──────────────────────────────
# 5. Search & Invoice
# ──────────────────────────────
with st.expander("🔍 Search Past Records"):
    query = st.text_input("Search by Name or Phone")
    if query:
        result = supabase.table("chipix_customers") \
            .select("*") \
            .or_(f"phone.ilike.%{query}%,name.ilike.%{query}%") \
            .order("timestamp", desc=True).execute()

        records = result.data if hasattr(result, "data") else []

        if records:
            for rec in records:
                st.markdown(f"---\n### 🎫 Record: **{rec['name']}** | `{rec['entry_type']}`")
                for k, v in rec.items():
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
                    buffer.write(pdf.output(dest="S").encode("latin-1"))
                    buffer.seek(0)
                    return buffer

                pdf_buf = generate_invoice(rec)
                st.download_button("📥 Download Invoice", data=pdf_buf, file_name=f"{rec['name']}_invoice.pdf")
        else:
            st.warning("No matching records found.")
