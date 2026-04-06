import streamlit as st
import pandas as pd

st.set_page_config(page_title="Bankroll Manager", layout="wide")

st.title("💼 Bankroll & Risk Manager")
st.write("Track your capital and calculate your 'Unit Size' to avoid blowing your account.")

# --- 1. SETTINGS ---
with st.sidebar:
    st.header("Financial Settings")
    total_bankroll = st.number_input("Total Betting Capital (ZAR)", min_value=100.0, value=2000.0, step=100.0)
    risk_percentage = st.slider("Risk per Bet (%)", 1, 10, 5)
    
# --- 2. RISK CALCULATOR ---
unit_size = total_bankroll * (risk_percentage / 100)

col1, col2, col3 = st.columns(3)
col1.metric("Total Bankroll", f"R{total_bankroll:,.2f}")
col2.metric("Risk Level", f"{risk_percentage}%")
col3.metric("Recommended Unit (Stake)", f"R{unit_size:,.2f}", delta_color="inverse")

st.info(f"💡 Based on your capital, you should only stake **R{unit_size:.2f}** per 3/4 system bet.")

st.divider()

# --- 3. PROFIT/LOSS TRACKER ---
st.subheader("📊 Performance History")

# Initialize session state for tracking if not already there
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Date', 'Bet Type', 'Stake', 'Result', 'Profit/Loss'])

# Entry Form
with st.expander("➕ Log a New Bet"):
    with st.form("bet_form"):
        date = st.date_input("Date")
        bet_type = st.selectbox("Type", ["System 3/4", "Straight Multi", "Single"])
        stake = st.number_input("Stake (ZAR)", value=unit_size)
        outcome = st.selectbox("Outcome", ["Pending", "Full Win", "Safety Net (3/4)", "Loss"])
        returns = st.number_input("Total Return (Payout)", value=0.0)
        
        if st.form_submit_button("Save to History"):
            p_l = returns - stake
            new_data = pd.DataFrame([[date, bet_type, stake, outcome, p_l]], 
                                    columns=['Date', 'Bet Type', 'Stake', 'Result', 'Profit/Loss'])
            st.session_state.history = pd.concat([st.session_state.history, new_data], ignore_index=True)
            st.success("Bet Logged!")

# Display Table
if not st.session_state.history.empty:
    st.dataframe(st.session_state.history, use_container_width=True)
    
    total_pl = st.session_state.history['Profit/Loss'].sum()
    if total_pl >= 0:
        st.success(f"**Total Net Profit: R{total_pl:.2f}**")
    else:
        st.error(f"**Total Net Loss: R{total_pl:.2f}**")
else:
    st.write("No bets logged yet. Start tracking to see your growth!")
