import streamlit as st
import pandas as pd

def get_fair_draw(h, a):
    hi, ai = 1/h, 1/a
    bal = 1 - abs(hi - ai)
    return 0.28 * bal

def calc_payout(odds, wins, wager):
    payout = 0
    spb = wager / 4
    for c in [(0,1,2), (0,1,3), (0,2,3), (1,2,3)]:
        if wins[c[0]] and wins[c[1]] and wins[c[2]]:
            payout += (odds[c[0]]*odds[c[1]]*odds[c[2]]*spb)
    return payout

st.title("🧪 Strategy Backtester")
uploaded = st.file_uploader("Upload E0.csv")

if uploaded:
    df = pd.read_csv(uploaded)
    # Automatically calculate EV for all matches
    df['EV_D'] = df.apply(lambda r: (get_fair_draw(r['AvgH'], r['AvgA']) * r['AvgD']) - 1, axis=1)
    
    # RANKING Strategy: Sort every game in the file by value
    sorted_df = df.sort_values('EV_D', ascending=False)
    
    bank, saved, hist = 500.0, 0.0, [500.0]
    
    # Simulate taking the Top 4 value bets in chunks
    for i in range(0, len(sorted_df)-4, 4):
        if bank <= 5: break
        chunk = sorted_df.iloc[i:i+4]
        
        wager = bank * 0.05
        odds = chunk['AvgD'].tolist()
        results = [1 if r == 'D' else 0 for r in chunk['FTR']]
        
        payout = calc_payout(odds, results, wager)
        net = payout - wager
        
        if net > 0:
            bank += (net * 0.8)
            saved += (net * 0.2)
        else:
            bank += net
        hist.append(bank + saved)

    st.metric("Final Balance", f"R{bank+saved:.2f}")
    st.line_chart(hist)
    st.write(f"Strategy automatically picked {len(sorted_df)//4 * 4} high-value matches.")
    
