import streamlit as st
import pandas as pd

def get_fair_probs(h_o, a_o):
    hi, ai = 1/h_o, 1/a_o
    bal = 1 - abs(hi - ai)
    fd = 0.26 * bal
    rem = 1.0 - fd
    return (hi/(hi+ai))*rem, fd, (ai/(hi+ai))*rem

def calc_3_4_payout(odds, results, wager):
    spb = wager / 4
    payout = 0
    combos = [(0,1,2), (0,1,3), (0,2,3), (1,2,3)]
    for c in combos:
        if results[c[0]] and results[c[1]] and results[c[2]]:
            payout += (odds[c[0]] * odds[c[1]] * odds[c[2]] * spb)
    return payout

st.title("🧪 Anti-Bankruptcy Strategy Tester")
uploaded = st.file_uploader("Upload E0.csv")

if uploaded:
    df = pd.read_csv(uploaded)
    min_edge = st.sidebar.slider("Min Value Edge %", 0, 15, 7) / 100
    
    # Pre-calculate Value for Draw (Option C)
    ev_data = []
    for _, row in df.iterrows():
        fh, fd, fa = get_fair_probs(row['AvgH'], row['AvgA'])
        ev_data.append({'EV_D': (fd*row['AvgD'])-1})
    df = pd.concat([df, pd.DataFrame(ev_data)], axis=1)

    # Strategy: Only bet if EV > min_edge
    v_df = df[df['EV_D'] >= min_edge].copy()
    
    bank = 500.0
    saved = 0.0
    history = [500.0]
    
    for i in range(0, len(v_df)-4, 4):
        if bank <= 5: break
        chunk = v_df.iloc[i:i+4]
        wager = bank * 0.05
        
        odds = chunk['AvgD'].tolist()
        wins = [1 if r == 'D' else 0 for r in chunk['FTR'].tolist()]
        
        payout = calc_3_4_payout(odds, wins, wager)
        net = payout - wager
        
        if net > 0:
            bank += (net * 0.8)
            saved += (net * 0.2)
        else:
            bank += net
        history.append(bank + saved)

    st.metric("Strategy Final Balance", f"R{bank+saved:.2f}")
    st.write(f"Matches traded: {len(v_df)} / Matches skipped: {len(df)-len(v_df)}")
    st.line_chart(history)
    
