import streamlit as st
import pandas as pd
import plotly.express as px
import time
import os

st.set_page_config(page_title="EBalaNCer Monitor", layout="wide")

# --- SIDEBAR CONTROLS ---
st.sidebar.title("Evaluation Controls")
# This allows you to switch between files
data_source = st.sidebar.selectbox(
    "Select Data Source", 
    ["mab_performance.csv", "baseline_rr.csv"],
    index=0
)

if st.sidebar.button('Clear Selected CSV'):
    with open(data_source, "w") as f:
        f.write("timestamp,choice,reward,load0,load1,traffic_type\n")
    st.sidebar.success(f"{data_source} Reset!")
    st.rerun()

# --- MAIN DASHBOARD ---
st.title("EBalaNCer: eBPF Adaptive Load Balancer")
st.markdown(f"**Monitoring File:** `{data_source}`")

metric_row = st.columns(3)
chart_row = st.columns(2)

if os.path.exists(data_source):
    try:
        df = pd.read_csv(data_source)
        
        if not df.empty:
            # Indicator logic
            if 'traffic_type' in df.columns:
                last_type = df['traffic_type'].iloc[-1]
                if last_type == 1.0:
                    st.warning("Context: Elephant Flow Detected")
                else:
                    st.info("Context: Mouse Flow Detected")

            last_entry = df.iloc[-1]
            
            with metric_row[0]:
                st.metric("Current Target", f"Node {int(last_entry['choice'])}")
            with metric_row[1]:
                st.metric("Last Reward", f"{last_entry['reward']:.2f}")
            with metric_row[2]:
                st.metric("Total Samples", len(df))

            with chart_row[0]:
                st.subheader("Reward History")
                # Using specific color based on source to make it clear which is which
                line_color = "blue" if data_source == "mab_performance.csv" else "orange"
                fig_reward = px.line(df, x=df.index, y="reward", 
                                     title=f"Performance: {data_source}",
                                     labels={'reward': 'Reward Score', 'index': 'Sample'},
                                     color_discrete_sequence=[line_color])
                st.plotly_chart(fig_reward, use_container_width=True)

            with chart_row[1]:
                st.subheader("Algorithm Confidence")
                df['cumulative_reward'] = df['reward'].cumsum()
                fig_cum = px.area(df, x=df.index, y='cumulative_reward', 
                                  title="Regret Minimization (Higher is Better)")
                st.plotly_chart(fig_cum, use_container_width=True)

    except Exception as e:
        st.error(f"Waiting for valid data in {data_source}...")

time.sleep(1)
st.rerun()