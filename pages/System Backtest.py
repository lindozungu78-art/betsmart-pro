import streamlit as st
import pandas as pd
import numpy as np

# --- 1. SMART ENGINE LOGIC ---
def get_engine_probs(h_odds, a_odds):
    """
    Advanced Poisson-based probability estimation.
    Calculates the 'Fair' probability of H/D/A results.
    """
    # Implied Bookie Probs
    h_implied = (1 / h_odds)
    a_implied = (1 / a_odds)
    
    # Draw Estimation based on parity
    balance_factor = 1 - abs(h_implied - a_implied)
    d_fair_prob = 0.26 * balance_factor
    
    # Re-normalize H and A
    remaining = 1.0 - d_fair_prob
    total_implied = h_implied + a_implied
    h_fair_prob = (h_implied / total_implied) * remaining
    a_fair_prob = (a_implied / total_implied) * remaining
    
    return h_fair_prob, d_fair_prob, a_fair_prob

def calc_system_3_4_payout(odds, results, set_wager):
    spb = set_wager / 4 
    payout = 0
    combos = [(0,1,2), (0,1,3), (0,2,3), (1,2,3)]
    for c in combos:
        if results[c[0]] and results[c[1]] and results[c[2]]:
            payout += (odds[c[0]] * odds[c[1]] * odds[c[2]] * spb)
    return payout

# --- 2. UI SETUP ---
st.set_page_config(page_title="Value Engine Backtester", layout="wide")
st.title("🛡️ Pro Value-Engine Backtester")
st.markdown("### Strategy: Positive Expected Value (+EV) Filtering")

# --- 3. SIDEBAR CONTROLS ---
st.sidebar.header("🕹️ Strategy Tuning")
min_edge = st.sidebar.slider("Minimum Value Edge (%)", 0.0, 15.0, 5.0) / 100
init_bank = st.sidebar.number_input("Starting Bankroll (ZAR)", value=500.0)
risk_pc = st.sidebar.slider("Risk per Set (%)", 1, 10, 5) / 100
rollover_pc = st.sidebar.slider("Profit Rollover (%)", 0, 100, 80) / 100
savings_pc = 1.0 - rollover_pc

# --- 4. THE DATA ENGINE ---
uploaded_file = st.file_uploader("Upload E0.csv")

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    # A. Run Engine Analytics on every match
    engine_results = []
    for idx, row in df.iterrows():
        h_fair, d_fair, a_fair = get_engine_probs(row['AvgH'], row['AvgA'])
        
        # Calculate EV for each outcome
        # EV = (Fair_Prob * Bookie_Odds) - 1
        ev_h = (h_fair * row['AvgH']) - 1
        ev_d = (d_fair * row['AvgD']) - 1
        ev_a = (a_fair * row['AvgA']) - 1
        
        engine_results.append({
            'EV_H': ev_h, 'EV_D': ev_d, 'EV_A': ev_a,
            'Fair_H': h_fair, 'Fair_D': d_fair, 'Fair_A': a_fair
        })
    
    engine_df = pd.concat([df, pd.DataFrame(engine_results)], axis=1)

    # B. Initialize Strategies
    strategies = {
        "Option A (Banker Value)": {"target": "H", "ev_col": "EV_H", "odds_col": "AvgH"},
        "Option C (Draw Value)": {"target": "D", "ev_col": "EV_D", "odds_col": "AvgD"},
        "Option D (Away Value)": {"target": "A", "ev_col": "EV_A", "odds_col": "AvgA"}
    }
    
    results_tracker = {}

    # C. Run Filtered Backtest
    for name, config in strategies.items():
        # FILTER: Only keep matches where our edge is higher than the threshold
        filtered_df = engine_df[engine_df[config['ev_col']] >= min_edge].copy()
        
        bank = init_bank
        saved = 0.0
        history = [init_bank]
        
        # Group filtered value bets into sets of 4
        for i in range(0, len(filtered_df)-4, 4):
            if bank <= 5: break
            
            chunk = filtered_df.iloc[i:i+4]
            wager = bank * risk_pc
            
            odds_list = chunk[config['odds_col']].tolist()
            # Win check: Did the result match our target (H/D/A)?
            wins = [1 if r == config['target'] else 0 for r in chunk['FTR'].tolist()]
            
            payout = calc_system_3_4_payout(odds_list, wins, wager)
            net_profit = payout - wager
            
            if net_profit > 0:
                bank += (net_profit * rollover_pc)
                saved += (net_profit * savings_pc)
            else:
                bank += net_profit
            
            history.append(bank + saved)
            
        results_tracker[name] = {"bank": bank, "saved": saved, "history": history, "total_bets": len(filtered_df)}

    # --- 5. RESULTS DISPLAY ---
    st.divider()
    cols = st.columns(3)
    for idx, (name, res) in enumerate(results_tracker.items()):
        with cols[idx]:
            total_equity = res['bank'] + res['saved']
            st.subheader(name)
            st.metric("Total Equity", f"R{total_equity:.2f}")
            st.write(f"📈 **Total Value Bets Found:** {res['total_bets']}")
            st.write(f"🔒 **Savings Account:** R{res['saved']:.2f}")
            st.line_chart(res['history'])
    
    st.info(f"The filter ignored matches with less than {min_edge*100}% expected value.")
else:
    st.warning("Upload E0.csv to run the Value-Filter simulation.")
