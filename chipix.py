import streamlit as st
from supabase import create_client
from fpdf import FPDF
from io import BytesIO
from datetime import datetime
import pytz

# ────────────────────────────────────────────────────────────────────────────────
# 1. SUPABASE SETUP
# ────────────────────────────────────────────────────────────────────────────────
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
ADMIN_USERNAME = st.secrets["ADMIN_USERNAME"]
ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
st.set_page_config(page_title="Chipix CRM", layout="wide")

ist = pytz.timezone('Asia/Kolkata')

# ────────────────────────────────────────────────────────────────────────────────
# 2. SESSION LOGIN
# ────────────────────────────────────────────────────────────────────────────────
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<h1 style='font-family: Arial; color: #1363DF;'>Chipix CRM Login</h1>", unsafe_allow_html=True)
    username = st.text_input("Admin Username")
    password = st.text_input("Admin Password", type="password")

    if username and password:
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("🚫 Incorrect credentials.")
    st.stop()

# ────────────────────────────────────────────────────────────────────────────────
# 3. HEADER + LOGOUT + CLOCK
# ────────────────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([0.85, 0.15])
with col1:
    st.markdown("<h1 style='font-family: Arial; color: #1363DF;'>Chipix CRM - Customer, Sales & Service Management</h1>", unsafe_allow_html=True)
with col2:
    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.experimental_rerun()

current_time = datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"### 🕒 Current IST Time: `{current_time}`")

# ────────────────────────────────────────────────────────────────────────────────
# 4. ADD ENTRY FORM
# ────────────────────────────────────────────────────────────────────────────────
with st.expander("➕ Add New Entry"):
    with st.form("entry_form", clear_on_submit=True):
        name = st.text_input("Customer Name")
        phone = st.text_input("Phone Number")
        entry_type = st.radio("Entry Type", ["Purchase", "Service"], horizontal=True)

        details = {}
        if entry_type == "Purchase":
            product = st.text_input("Product Name")
            price = st.number_input("Amount Paid (₹)", min_value=0.0, format="%.2f")
            warranty = st.selectbox("Warranty Period", ["1 Month", "3 Months", "6 Months", "1 Year", "2 Years"])
            details = {"product": product, "price": price, "warranty": warranty}
        else:
            item = st.text_input("Electronic Item")
            issue = st.text_area("Issue Description")
            status = st.selectbox("Initial Status", ["Pending", "In Progress", "Completed"])
            details = {"item": item, "issue": issue, "status": status}

        submitted = st.form_submit_button("Submit Entry")

        if submitted:
            if not name.replace(" ", "").isalpha():
                st.error("❌ Name must contain only letters.")
            elif not phone.isdigit() or len(phone) != 10:
                st.error("❌ Phone number must be exactly 10 digits.")
            elif not all(details.values()):
                st.error("❌ Please fill all required fields.")
            else:
                timestamp_dt = datetime.now(ist)
                timestamp = timestamp_dt.isoformat()
                pretty_time = timestamp_dt.strftime('%d-%m-%Y %I:%M:%S %p')

                entry = {
                    "name": name,
                    "phone": phone,
                    "entry_type": entry_type,
                    "timestamp": timestamp,
                    "invoice_time": pretty_time,
                    **details
                }

                response = supabase.table("chipix_customers").insert(entry).execute()

                if hasattr(response, "data") and response.data:
                    st.success(f"✅ {entry_type} entry for **{name}** recorded.")
                    st.info(f"🕒 Invoice generated at `{pretty_time}`")
                else:
                    error_msg = getattr(getattr(response, "error", None), "message", "Unknown error")
                    st.error(f"❌ Failed to add entry. Error: {error_msg}")

# ────────────────────────────────────────────────────────────────────────────────
# 5. FETCH RECORDS
# ────────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_customers():
    res = supabase.table("chipix_customers").select("*").order("timestamp", desc=True).execute()
    return res.data if hasattr(res, "data") else []

# ────────────────────────────────────────────────────────────────────────────────
# 6. PDF GENERATOR
# ────────────────────────────────────────────────────────────────────────────────
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
    buffer.write(pdf.output(dest='S').encode('latin-1'))
    buffer.seek(0)
    return buffer

# ────────────────────────────────────────────────────────────────────────────────
# 7. SEARCH & MANAGE
# ────────────────────────────────────────────────────────────────────────────────
with st.expander("🔍 Search & Manage Customer"):
    query = st.text_input("Search by Name or Phone")
    data = fetch_customers()

    if query:
        filtered = [e for e in data if query.lower() in e.get("name", "").lower() or query in e.get("phone", "")]
        if filtered:
            st.write(f"📄 Found {len(filtered)} matching records:")
            for r in filtered:
                if r.get('entry_type') == 'Purchase':
                    st.success(f"🛒 *{r['name']}* | {r['phone']} | {r['product']} | ₹{r['price']} | {r['warranty']}")
                    if st.button(f"🖨 Generate Invoice for {r['name']}", key=f"invoice_{r['id']}"):
                        pdf_buf = generate_invoice(r)
                        st.download_button("📥 Download Invoice PDF", data=pdf_buf, file_name=f"{r['name']}_invoice.pdf", key=f"dl_{r['id']}")
                else:
                    st.info(f"🛠 *{r['name']}* | {r['phone']} | {r['item']} | {r['issue']} | Status: {r['status']}")
                    cols = st.columns([3, 3, 3])
                    cols[0].markdown(f"**{r['name']}** | {r['item']}")
                    new_status = cols[1].selectbox("Update Status", ["Pending", "In Progress", "Completed"],
                                                   index=["Pending", "In Progress", "Completed"].index(r["status"]),
                                                   key=str(r["id"]))
                    if new_status != r["status"]:
                        supabase.table("chipix_customers").update({"status": new_status}).eq("id", r["id"]).execute()
                        st.success(f"✅ Status updated for {r['name']}")
        else:
            st.warning("No matching records found.")
