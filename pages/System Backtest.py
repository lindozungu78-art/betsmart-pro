import streamlit as st
import pandas as pd
import io

# --- 1. CORE LOGIC ---
def calculate_draw_prob(h_prob, a_prob):
    balance_factor = 1 - abs(h_prob - a_prob) / 100
    return round(26.0 * balance_factor, 1)

def calc_system_3_4_payout(odds, results, set_wager):
    spb = set_wager / 4 
    payout = 0
    combos = [(0,1,2), (0,1,3), (0,2,3), (1,2,3)]
    for c in combos:
        if results[c[0]] and results[c[1]] and results[c[2]]:
            payout += (odds[c[0]] * odds[c[1]] * odds[c[2]] * spb)
    return payout

# --- 2. UI SETUP ---
st.set_page_config(page_title="Pro Backtester", layout="wide")
st.title("🧪 4x4 Multi-Strategy Backtester")

# --- 3. ADJUSTABLE SETTINGS ---
st.sidebar.header("💰 Bankroll Management")
init_bank = st.sidebar.number_input("Starting Bankroll (ZAR)", value=500.0)
risk_pc = st.sidebar.slider("Risk per Set (%)", 1, 10, 5) / 100
rollover_pc = st.sidebar.slider("Profit to Rollover (%)", 0, 100, 80) / 100
savings_pc = 1.0 - rollover_pc

# --- 4. THE FILE FIX ---
# We removed type="csv" to prevent mobile grey-out issues
uploaded_file = st.file_uploader("Select E0.csv from your device")

if uploaded_file is not None:
    try:
        # Read the file
        df = pd.read_csv(uploaded_file)
        
        # Check for required columns
        required = ['AvgH', 'AvgA', 'FTR']
        if not all(col in df.columns for col in required):
            st.error(f"File missing required columns: {required}")
            st.stop()

        df['H_Prob'] = (1 / df['AvgH']) * 100
        df['A_Prob'] = (1 / df['AvgA']) * 100
        df['D_Prob_Engine'] = df.apply(lambda x: calculate_draw_prob(x['H_Prob'], x['A_Prob']), axis=1)

        strategies = {
            "Option A (Bankers)": {"bank": init_bank, "saved": 0.0, "history": [init_bank]},
            "Option B (Home Edge)": {"bank": init_bank, "saved": 0.0, "history": [init_bank]},
            "Option C (Draw/Value)": {"bank": init_bank, "saved": 0.0, "history": [init_bank]},
            "Option D (Underdogs)": {"bank": init_bank, "saved": 0.0, "history": [init_bank]}
        }

        # Simulation Loop
        for i in range(0, len(df)-4, 4):
            chunk = df.iloc[i:i+4]
            sets = {
                "Option A (Bankers)": chunk.sort_values('H_Prob', ascending=False),
                "Option B (Home Edge)": chunk,
                "Option C (Draw/Value)": chunk.sort_values('D_Prob_Engine', ascending=False),
                "Option D (Underdogs)": chunk.sort_values('H_Prob', ascending=True)
            }

            for name, data in sets.items():
                res = strategies[name]
                if res['bank'] <= 5: continue
                
                wager = res['bank'] * risk_pc
                odds = data['AvgH'].tolist()
                wins = [1 if r == 'H' else 0 for r in data['FTR'].tolist()]
                
                payout = calc_system_3_4_payout(odds, wins, wager)
                net_profit = payout - wager
                
                if net_profit > 0:
                    res['bank'] += (net_profit * rollover_pc)
                    res['saved'] += (net_profit * savings_pc)
                else:
                    res['bank'] += net_profit
                
                res['history'].append(res['bank'])

        # --- 5. RESULTS ---
        st.divider()
        cols = st.columns(4)
        for idx, (name, res) in enumerate(strategies.items()):
            with cols[idx]:
                total = res['bank'] + res['saved']
                st.subheader(name)
                st.metric("Total Equity", f"R{total:.2f}")
                st.write(f"🏦 Bank: R{res['bank']:.2f}")
                st.write(f"🔒 Saved: R{res['saved']:.2f}")
                st.line_chart(res['history'])
        
        st.success("Analysis Complete!")

    except Exception as e:
        st.error(f"Error reading file: {e}")
else:
    st.info("👆 Tap 'Browse files' and select your E0.csv file.")
    
