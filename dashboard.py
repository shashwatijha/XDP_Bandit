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
        f.write("timestamp,choice,reward,load0,load1,traffic_type\n")
    st.success("CSV Reset Done")
    st.rerun()

metric_row = st.columns(3)
chart_row = st.columns(2)

if os.path.exists("mab_performance.csv"):
    try:
        df = pd.read_csv("mab_performance.csv")
        
        if not df.empty:
            # Traffic Awareness Indicator
            if 'traffic_type' in df.columns:
                last_type = df['traffic_type'].iloc[-1]
                if last_type == 1.0:
                    st.warning("Elephant Flow Detected: Prioritizing Throughput")
                else:
                    st.info("Mouse Flow Detected: Prioritizing Latency")

            last_entry = df.iloc[-1]
            
            with metric_row[0]:
                st.metric("Current Target", f"Node {int(last_entry['choice'])}")
            with metric_row[1]:
                st.metric("Last Reward", f"{last_entry['reward']:.2f}")
            with metric_row[2]:
                st.metric("Total Samples", len(df))

            with chart_row[0]:
                st.subheader("Reward History")
                fig_reward = px.line(df, x=df.index, y="reward", 
                                     title="Learning Performance",
                                     labels={'reward': 'Reward Score', 'index': 'Sample'})
                st.plotly_chart(fig_reward, use_container_width=True)

            with chart_row[1]:
                st.subheader("Load Balancing Split")
                load0 = last_entry['load0']
                load1 = last_entry['load1']
                fig_load = px.pie(values=[load0, load1], names=['Node 1 (.2)', 'Node 2 (.3)'],
                                  title="Packet Distribution",
                                  color_discrete_sequence=px.colors.qualitative.Set3)
                st.plotly_chart(fig_load, use_container_width=True)

            # Cumulative Reward Path
            st.subheader("Algorithm Confidence (Cumulative Reward)")
            df['cumulative_reward'] = df['reward'].cumsum()
            fig_cum = px.area(df, x=df.index, y='cumulative_reward', title="Regret Minimization Trend")
            st.plotly_chart(fig_cum, use_container_width=True)

    except Exception as e:
        st.error(f"Waiting for valid CSV data... {e}")

time.sleep(1)
st.rerun()