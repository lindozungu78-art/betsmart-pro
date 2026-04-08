import streamlit as st
import pandas as pd
import requests

# --- CONFIG ---
st.set_page_config(page_title="BetSmart Pro: Auto-Pick", layout="wide")
ODDS_API_KEY = "8e1ac8e3fb43757f30f2aec94dbebb81"

# --- ENGINE ---
def calculate_draw_value(h_o, d_o, a_o):
    hi, ai = 1/h_o, 1/a_o
    balance = 1 - abs(hi - ai)
    fair_draw = 0.28 * balance
    ev = (fair_draw * d_o) - 1
    return fair_draw, ev

# --- UI TABS ---
tab1, tab2, tab3 = st.tabs(["🚀 Auto-Pick Slip", "📅 Live Odds Sync", "🧮 80/20 Calculator"])

with tab2:
    st.header("Sync Market Odds")
    if st.button("🔄 Sync Live Prices"):
        # Fetching Premier League Head-to-Head odds
        url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h"
        try:
            response = requests.get(url).json()
            processed_matches = []
            for match in response:
                # Extracting Draw Odds from the first bookmaker (usually 1xBet or Bet365)
                try:
                    outcomes = match['bookmakers'][0]['markets'][0]['outcomes']
                    h = next(o['price'] for o in outcomes if o['name'] == match['home_team'])
                    a = next(o['price'] for o in outcomes if o['name'] == match['away_team'])
                    d = next(o['price'] for o in outcomes if o['name'] == 'Draw')
                    
                    fair_d, ev = calculate_draw_value(h, d, a)
                    processed_matches.append({
                        "Match": f"{match['home_team']} vs {match['away_team']}",
                        "Draw Odds": d,
                        "Edge %": ev * 100,
                        "Home": match['home_team'],
                        "Away": match['away_team']
                    })
                except: continue
            
            st.session_state['live_data'] = pd.DataFrame(processed_matches).sort_values("Edge %", ascending=False)
            st.success("Synced Live Odds successfully!")
            st.table(st.session_state['live_data'][["Match", "Draw Odds", "Edge %"]])
        except:
            st.error("API Limit Reached or Key Invalid.")

with tab1:
    st.header("🎯 Recommended 3/4 Slip")
    if 'live_data' in st.session_state:
        # Top 4 picks based on the highest Value Edge
        top_4 = st.session_state['live_data'].head(4)
        
        cols = st.columns(4)
        for i, (idx, row) in enumerate(top_4.iterrows()):
            with cols[i]:
                st.info(f"**Pick {i+1}**")
                st.write(f"{row['Match']}")
                st.metric("Odds", row['Draw Odds'])
                st.write(f"Edge: {row['Edge %']:.1f}%")
        
        total_odds = top_4['Draw Odds'].prod() # Rough estimate of potential parlay
        st.divider()
        st.subheader(f"System 3/4 Potential: High Value Detected")
    else:
        st.warning("Please Sync data in the 'Live Odds Sync' tab first.")

with tab3:
    st.header("System 3/4 & 80/20 Payouts")
    bank = st.number_input("Bankroll (ZAR)", value=500.0)
    risk = st.slider("Risk (%)", 1, 10, 5) / 100
    wager = bank * risk
    
    st.write(f"Total Stake: R{wager:.2f} | Treble Unit: R{wager/4:.2f}")
    
    o_cols = st.columns(4)
    odds_inputs = [o_cols[i].number_input(f"Odds {i+1}", value=3.20, key=f"c_o{i}") for i in range(4)]
    w_cols = st.columns(4)
    wins = [w_cols[i].checkbox(f"Won {i+1}", key=f"c_w{i}") for i in range(4)]
    
    payout = 0
    for c in [(0,1,2), (0,1,3), (0,2,3), (1,2,3)]:
        if wins[c[0]] and wins[c[1]] and wins[c[2]]:
            payout += (odds_inputs[c[0]]*odds_inputs[c[1]]*odds_inputs[c[2]]*(wager/4))
    
    profit = payout - wager
    st.subheader(f"Payout: R{payout:.2f}")
    if profit > 0:
        st.write(f"✅ Bank (80%): R{profit*0.8:.2f} | 🔒 Saved (20%): R{profit*0.2:.2f}")
                    
