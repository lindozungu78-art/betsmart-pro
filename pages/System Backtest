import streamlit as st
import pandas as pd

# --- 1. ENGINE LOGIC (Standardized with your Main App) ---
def calculate_draw_prob(h_prob, a_prob):
    # This matches the 'Option C' logic from your live engine
    balance_factor = 1 - abs(h_prob - a_prob) / 100
    return round(26.0 * balance_factor, 1)

def calc_system_3_4_payout(odds, results, set_wager):
    """
    Calculates the payout for a System 3/4 (4 Trebles).
    odds: list of 4 odds (e.g. [2.1, 1.8, 3.2, 1.5])
    results: list of 4 booleans (True if the match was a win)
    set_wager: the total ZAR risked on this 4-match set
    """
    spb = set_wager / 4  # Stake per Treble (Total / 4 combinations)
    payout = 0
    # The 4 possible Treble combinations in a 3/4 system:
    combos = [(0,1,2), (0,1,3), (0,2,3), (1,2,3)]
    
    for c in combos:
        # Check if all 3 matches in this treble were wins
        if results[c[0]] and results[c[1]] and results[c[2]]:
            payout += (odds[c[0]] * odds[c[1]] * odds[c[2]] * spb)
    return payout

# --- 2. UI SETUP ---
st.set_page_config(page_title="Pro Backtester", layout="wide")
st.title("🧪 4x4 Multi-Strategy Backtester")
st.subheader("80/20 Compounding & Savings Engine")

# --- 3. ADJUSTABLE SETTINGS (Sidebar) ---
st.sidebar.header("💰 Bankroll Management")
init_bank = st.sidebar.number_input("Starting Bankroll (ZAR)", value=500.0, step=50.0)
risk_pc = st.sidebar.slider("Risk per Set (%)", 1, 10, 5) / 100
rollover_pc = st.sidebar.slider("Profit to Rollover (%)", 0, 100, 80) / 100
savings_pc = 1.0 - rollover_pc

st.sidebar.markdown(f"""
**Strategy Rules:**
- **Stake:** {risk_pc*100}% of current bankroll.
- **Winnings:** {rollover_pc*100}% stays in bankroll.
- **Savings:** {savings_pc*100}% moved to bank.
""")

# --- 4. DATA LOADING ---
uploaded_file = st.file_uploader("Upload 'E0.csv' to start", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # Calculate probabilities based on market average odds in the CSV
    df['H_Prob'] = (1 / df['AvgH']) * 100
    df['A_Prob'] = (1 / df['AvgA']) * 100
    df['D_Prob_Engine'] = df.apply(lambda x: calculate_draw_prob(x['H_Prob'], x['A_Prob']), axis=1)

    # Initialize Tracking for all 4 Engine Options
    strategies = {
        "Option A (Bankers)": {"bank": init_bank, "saved": 0.0, "history": [init_bank]},
        "Option B (Home Edge)": {"bank": init_bank, "saved": 0.0, "history": [init_bank]},
        "Option C (Draw/Value)": {"bank": init_bank, "saved": 0.0, "history": [init_bank]},
        "Option D (Underdogs)": {"bank": init_bank, "saved": 0.0, "history": [init_bank]}
    }

    # Simulation: Group data into sets of 4 matches
    for i in range(0, len(df)-4, 4):
        chunk = df.iloc[i:i+4]
        
        # Sort current chunk into the 4 Engine styles
        sets = {
            "Option A (Bankers)": chunk.sort_values('H_Prob', ascending=False),
            "Option B (Home Edge)": chunk, # Sequential baseline
            "Option C (Draw/Value)": chunk.sort_values('D_Prob_Engine', ascending=False),
            "Option D (Underdogs)": chunk.sort_values('H_Prob', ascending=True)
        }

        for name, data in sets.items():
            current_bank = strategies[name]['bank']
            if current_bank <= 10: continue # Stop if bank is too low (R10)
            
            # 1. Place the Bet
            wager = current_bank * risk_pc
            odds = data['AvgH'].tolist() # Testing against Home Win odds
            wins = [1 if r == 'H' else 0 for r in data['FTR'].tolist()]
            
            # 2. Calculate Outcome
            payout = calc_system_3_4_payout(odds, wins, wager)
            net_profit = payout - wager
            
            # 3. Apply 80/20 Rule
            if net_profit > 0:
                strategies[name]['bank'] += (net_profit * rollover_pc)
                strategies[name]['saved'] += (net_profit * savings_pc)
            else:
                strategies[name]['bank'] += net_profit # Deduct full loss
            
            strategies[name]['history'].append(strategies[name]['bank'])

    # --- 5. RESULTS DISPLAY ---
    st.divider()
    cols = st.columns(4)
    for idx, (name, res) in enumerate(strategies.items()):
        with cols[idx]:
            total_equity = res['bank'] + res['saved']
            growth = ((total_equity - init_bank) / init_bank) * 100
            
            st.subheader(name)
            st.metric("Total Equity", f"R{total_equity:.2f}", f"{growth:.1f}%")
            st.write(f"🏦 **Active Bank:** R{res['bank']:.2f}")
            st.write(f"🔒 **Savings:** R{res['saved']:.2f}")
            st.line_chart(res['history'])

    st.success("Analysis complete. Review the 'Savings' to see your actual locked-in profit.")
else:
    st.warning("Awaiting E0.csv file upload...")
