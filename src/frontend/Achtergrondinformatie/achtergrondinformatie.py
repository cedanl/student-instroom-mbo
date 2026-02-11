# Home.py
import streamlit as st

title = "Home"
icon = ":material/home:"

st.markdown(
    """
    ## 🚀 Deze app is gebouwd op basis van de CEDA Streamlit App Template! 
    <span style="font-size: 0.85em;"><em>Zie de repository: (https://github.com/cedanl/streamlit-app-template).</em></span><br><br>
    
    
    De CEDA Streamlit App Template biedt onderzoekers en data scientists een snelle en gestructureerde basis voor het bouwen van een interactieve web applicatie 
    voor data analyse en visualisatie. 
    
    Dit template is uitermate geschikt voor het bouwen van:
    - Data analysis dashboards
    - Interactive visualizations
    - Machine learning demos
    - Research presentation tools
      
    <br>
   🙏 Met dank aan het CEDA team voor het bouwen van deze app en speciale dank aan <span style="color: #FFEB3B;">Ash</span> en <span style="color: #FFEB3B;">Tomer</span>!
    """,
    unsafe_allow_html=True
)