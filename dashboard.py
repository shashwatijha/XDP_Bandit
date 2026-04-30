import streamlit as st
import pandas as pd
import plotly.express as px
import time
import os

st.set_page_config(page_title="LinUCB XDP Monitor", layout="wide")

st.title("LinUCB MAB XDP Load Balancer Monitor")
st.markdown("Real-time visualization of kernel-level routing decisions.")

if st.button('Clear Data / Reset Stats'):
    with open("mab_performance.csv", "w") as f:
        f.write("timestamp,choice,reward,load0,load1\n")
    st.success("CSV Reset! Charts will clear on next update.")
    st.rerun()
# Create placeholders for metrics and charts
metric_row = st.columns(3)
chart_row = st.columns(2)

while True:
    if os.path.exists("mab_performance.csv"):
        # Load the data
        df = pd.read_csv("mab_performance.csv")
        
        if not df.empty:
            # Current Status Metrics
            last_entry = df.iloc[-1]
            with metric_row[0]:
                st.metric("Current Target", f"Node {int(last_entry['choice'])}")
            with metric_row[1]:
                st.metric("Last Reward", f"{last_entry['reward']:.2f}")
            with metric_row[2]:
                st.metric("Total Samples", len(df))

            # Reward Over Time Chart
            with chart_row[0]:
                st.subheader("Reward History")
                fig_reward = px.line(df, x=df.index, y="reward", 
                                     title="Performance (Higher is Better)",
                                     labels={'reward': 'Reward Score', 'index': 'Sample'})
                st.plotly_chart(fig_reward, use_container_width=True)

            # Load Distribution Chart
            with chart_row[1]:
                st.subheader("Load Balancing Split")
                # Sum the loads from the columns
                load0 = last_entry['load0']
                load1 = last_entry['load1']
                fig_load = px.pie(values=[load0, load1], names=['Node 1 (.2)', 'Node 2 (.3)'],
                                  title="Accumulated Packet Load",
                                  color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_load, use_container_width=True)

        

    time.sleep(1) # Refresh every second
    st.rerun()