import streamlit as st
import pandas as pd

# --- 1. CORE MATH ---
def calculate_draw_prob(h_prob, a_prob):
    balance_factor = 1 - abs(h_prob - a_prob) / 100
    return round(26.0 * balance_factor, 1)

def calc_system_3_4_payout(odds, results, set_wager):
    spb = set_wager / 4 
    payout = 0
    combos = [(0,1,2), (0,1,3), (0,2,3), (1,2,3)]
    for c in combos:
        # Check if 3 out of 3 in the treble are wins
        if results[c[0]] and results[c[1]] and results[c[2]]:
            payout += (odds[c[0]] * odds[c[1]] * odds[c[2]] * spb)
    return payout

# --- 2. UI ---
st.set_page_config(page_title="Pro Backtester", layout="wide")
st.title("🧪 4x4 Multi-Strategy Backtester")

# --- 3. ADJUSTABLE SETTINGS ---
st.sidebar.header("💰 Money Management")
init_bank = st.sidebar.number_input("Starting Bankroll (ZAR)", value=500.0)
risk_pc = st.sidebar.slider("Risk per Set (%)", 1, 10, 5) / 100
rollover_pc = st.sidebar.slider("Profit Rollover (%)", 0, 100, 80) / 100
savings_pc = 1.0 - rollover_pc

# --- 4. THE DATA ENGINE ---
uploaded_file = st.file_uploader("Select E0.csv")

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    # Calculate Base Probabilities
    df['H_Prob'] = (1 / df['AvgH']) * 100
    df['A_Prob'] = (1 / df['AvgA']) * 100
    df['D_Prob_Engine'] = df.apply(lambda x: calculate_draw_prob(x['H_Prob'], x['A_Prob']), axis=1)

    # We initialize the dictionary with fresh data for each run
    strategies = {
        "Option A (Bankers)": {"bank": init_bank, "saved": 0.0, "history": [init_bank]},
        "Option B (Home Edge)": {"bank": init_bank, "saved": 0.0, "history": [init_bank]},
        "Option C (Draw/Value)": {"bank": init_bank, "saved": 0.0, "history": [init_bank]},
        "Option D (Underdogs)": {"bank": init_bank, "saved": 0.0, "history": [init_bank]}
    }

    # IMPORTANT: We run each strategy INDEPENDENTLY so they don't interfere
    for strat_name in strategies.keys():
        # Sort the entire season based on the strategy's goal
        if strat_name == "Option A (Bankers)":
            sim_df = df.sort_values('H_Prob', ascending=False)
        elif strat_name == "Option C (Draw/Value)":
            sim_df = df.sort_values('D_Prob_Engine', ascending=False)
        elif strat_name == "Option D (Underdogs)":
            sim_df = df.sort_values('H_Prob', ascending=True)
        else: # Option B - Home Edge (Baseline)
            sim_df = df.copy()

        # Group into sets of 4
        for i in range(0, len(sim_df)-4, 4):
            chunk = sim_df.iloc[i:i+4]
            res = strategies[strat_name]
            
            if res['bank'] <= 1.0: # Stop if basically bust
                break
                
            # Place the 3/4 System Bet
            set_wager = res['bank'] * risk_pc
            odds = chunk['AvgH'].tolist()
            wins = [1 if r == 'H' else 0 for r in chunk['FTR'].tolist()]
            
            payout = calc_system_3_4_payout(odds, wins, set_wager)
            net_profit = payout - set_wager
            
            # 80/20 Math
            if net_profit > 0:
                res['bank'] += (net_profit * rollover_pc)
                res['saved'] += (net_profit * savings_pc)
            else:
                res['bank'] += net_profit # Negative profit = Loss
            
            res['history'].append(res['bank'] + res['saved'])

    # --- 5. DISPLAY RESULTS ---
    st.divider()
    cols = st.columns(4)
    for idx, (name, res) in enumerate(strategies.items()):
        with cols[idx]:
            total_equity = res['bank'] + res['saved']
            st.subheader(name)
            st.metric("Total Equity", f"R{total_equity:.2f}")
            st.write(f"🏦 Bank: R{res['bank']:.2f}")
            st.write(f"🔒 Saved: R{res['saved']:.2f}")
            # Line chart of Total Equity
            st.line_chart(res['history'])
    
    st.success("Simulation Complete! Notice how Option D usually has higher volatility.")
else:
    st.info("Upload E0.csv to generate strategy comparisons.")
    
