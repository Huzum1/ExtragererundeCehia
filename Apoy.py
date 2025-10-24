import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
from datetime import datetime
import re

st.set_page_config(page_title="Lottery Data Extractor", page_icon="🎰", layout="wide")

# Inițializare session state
if 'saved_sources' not in st.session_state:
    st.session_state.saved_sources = []

if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = None

st.title("🎰 Lottery Data Extractor")
st.markdown("Extrage date istorice de la diverse loterii")

# Sidebar pentru surse salvate
with st.sidebar:
    st.header("📋 Surse Salvate")
    
    if st.session_state.saved_sources:
        for idx, source in enumerate(st.session_state.saved_sources):
            with st.expander(f"{source['name']}"):
                st.write(f"**URL:** {source['url']}")
                st.write(f"**Tip:** {source['type']}")
                if st.button(f"Șterge", key=f"del_{idx}"):
                    st.session_state.saved_sources.pop(idx)
                    st.rerun()
    else:
        st.info("Nicio sursă salvată încă")

# Tab-uri principale
tab1, tab2, tab3 = st.tabs(["➕ Adaugă Sursă", "📊 Extrage Date", "ℹ️ Info"])

with tab1:
    st.header("Adaugă o nouă sursă de loterie")
    
    col1, col2 = st.columns(2)
    
    with col1:
        source_name = st.text_input("Nume sursă", placeholder="ex: Cehia Keno Rapido")
        source_url = st.text_input("URL complet", placeholder="https://...")
        
    with col2:
        source_type = st.selectbox(
            "Tip loterie",
            ["Keno", "Loto", "Powerball", "EuroJackpot", "Rapido", "Altul"]
        )
        
        numbers_count = st.number_input("Câte numere se extrag", min_value=1, max_value=100, value=20)
    
    numbers_range = st.text_input("Interval numere", placeholder="ex: 1-80 sau 1-66", value="1-80")
    
    # Informații despre selectori CSS/HTML
    with st.expander("⚙️ Setări Avansate (Opțional)"):
        st.markdown("Ajută aplicația să găsească datele pe pagină:")
        css_selector = st.text_input("Selector CSS pentru tabel/rezultate", placeholder="ex: .results-table, #draws")
        date_format = st.text_input("Format dată", placeholder="ex: DD.MM.YYYY sau YYYY-MM-DD", value="DD.MM.YYYY")
    
    if st.button("💾 Salvează Sursa", type="primary"):
        if source_name and source_url:
            new_source = {
                'name': source_name,
                'url': source_url,
                'type': source_type,
                'numbers_count': numbers_count,
                'numbers_range': numbers_range,
                'css_selector': css_selector if css_selector else None,
                'date_format': date_format
            }
            st.session_state.saved_sources.append(new_source)
            st.success(f"✅ Sursa '{source_name}' a fost salvată!")
        else:
            st.error("Te rog completează cel puțin numele și URL-ul!")

with tab2:
    st.header("Extrage date de la sursele salvate")
    
    if not st.session_state.saved_sources:
        st.warning("Nu ai surse salvate! Adaugă o sursă în tab-ul 'Adaugă Sursă'")
    else:
        selected_source = st.selectbox(
            "Alege sursa",
            range(len(st.session_state.saved_sources)),
            format_func=lambda x: st.session_state.saved_sources[x]['name']
        )
        
        source = st.session_state.saved_sources[selected_source]
        
        col1, col2 = st.columns(2)
        with col1:
            num_rounds = st.number_input("Câte runde să extrag", min_value=1, max_value=5000, value=100)
        
        with col2:
            st.write(f"**URL:** {source['url']}")
            st.write(f"**Tip:** {source['type']}")
        
        use_selenium = st.checkbox("🤖 Folosește browser automat (pentru site-uri dinamice)", value=False)
        
        if st.button("🔍 Extrage Date", type="primary"):
            with st.spinner(f"Extrag {num_rounds} runde de la {source['name']}..."):
                try:
                    results = []
                    
                    if use_selenium:
                        # Folosește Selenium pentru site-uri cu butoane "Load More"
                        try:
                            from selenium import webdriver
                            from selenium.webdriver.common.by import By
                            from selenium.webdriver.support.ui import WebDriverWait
                            from selenium.webdriver.support import expected_conditions as EC
                            from selenium.webdriver.chrome.options import Options
                            import time
                            
                            st.info("🤖 Pornesc browser-ul automat...")
                            
                            # Configurare Chrome headless
                            chrome_options = Options()
                            chrome_options.add_argument('--headless')
                            chrome_options.add_argument('--no-sandbox')
                            chrome_options.add_argument('--disable-dev-shm-usage')
                            chrome_options.add_argument('--disable-gpu')
                            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                            
                            driver = webdriver.Chrome(options=chrome_options)
                            driver.get(source['url'])
                            
                            # Așteaptă încărcarea paginii
                            time.sleep(3)
                            
                            # Apasă butonul "Încarcă mai multe" până obținem destule rezultate
                            click_count = 0
                            max_clicks = (num_rounds // 20) + 2  # Estimare câte clickuri sunt necesare
                            
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            for i in range(max_clicks):
                                try:
                                    # Caută butonul cu diverse variante de text
                                    button_selectors = [
                                        "//button[contains(text(), 'NAČÍST DALŠÍ')]",
                                        "//button[contains(text(), 'Load more')]",
                                        "//button[contains(text(), 'Încarcă mai multe')]",
                                        "//a[contains(text(), 'NAČÍST DALŠÍ')]",
                                        "//button[contains(@class, 'load-more')]"
                                    ]
                                    
                                    button_found = False
                                    for selector in button_selectors:
                                        try:
                                            button = WebDriverWait(driver, 5).until(
                                                EC.element_to_be_clickable((By.XPATH, selector))
                                            )
                                            
                                            # Scroll la buton
                                            driver.execute_script("arguments[0].scrollIntoView(true);", button)
                                            time.sleep(1)
                                            
                                            # Click
                                            button.click()
                                            click_count += 1
                                            button_found = True
                                            
                                            status_text.text(f"📥 Click #{click_count} - Aștept încărcarea...")
                                            progress_bar.progress(min((i + 1) / max_clicks, 1.0))
                                            
                                            # Așteaptă încărcarea datelor noi
                                            time.sleep(2)
                                            break
                                        except:
                                            continue
                                    
                                    if not button_found:
                                        status_text.text("✅ Nu mai sunt date de încărcat")
                                        break
                                        
                                except Exception as e:
                                    status_text.text(f"ℹ️ Am terminat de încărcat date (Click #{click_count})")
                                    break
                            
                            progress_bar.empty()
                            status_text.empty()
                            
                            # Extrage datele finale
                            soup = BeautifulSoup(driver.page_source, 'html.parser')
                            driver.quit()
                            
                            st.success(f"✅ Am dat {click_count} click-uri pe buton!")
                            
                        except ImportError:
                            st.error("❌ Selenium nu este instalat! Instalează: pip install selenium")
                            st.info("📝 Încerc cu metoda standard (fără click automat)...")
                            use_selenium = False
                    
                    if not use_selenium:
                        # Metodă standard - doar prima pagină
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                        }
                        
                        response = requests.get(source['url'], headers=headers, timeout=10)
                        response.raise_for_status()
                        soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Extrage datele din HTML
                    # Metodă generică - caută tabele și liste
                    tables = soup.find_all('table')
                    
                    if tables:
                        st.info(f"Am găsit {len(tables)} tabel(e) pe pagină")
                        
                        # Procesează primul tabel
                        for row in tables[0].find_all('tr')[1:num_rounds+1]:  # Skip header
                            cells = row.find_all(['td', 'th'])
                            if len(cells) >= 2:
                                row_data = [cell.get_text(strip=True) for cell in cells]
                                results.append(row_data)
                    
                    # Dacă nu găsim tabele, căutăm alte structuri
                    if not results:
                        # Caută div-uri sau span-uri cu clase comune
                        divs = soup.find_all('div', class_=re.compile(r'result|draw|number|winning'))
                        if divs:
                            st.info(f"Am găsit {len(divs)} elemente cu rezultate")
                    
                    if results:
                        # Crează DataFrame
                        df = pd.DataFrame(results)
                        st.session_state.extracted_data = df
                        
                        st.success(f"✅ Am extras {len(results)} runde!")
                        
                        st.dataframe(df, use_container_width=True)
                        
                        # Download buttons
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            csv = df.to_csv(index=False)
                            st.download_button(
                                "📥 Download CSV",
                                csv,
                                f"{source['name']}_data.csv",
                                "text/csv"
                            )
                        
                        with col2:
                            excel_buffer = pd.ExcelWriter('temp.xlsx', engine='openpyxl')
                            df.to_excel(excel_buffer, index=False)
                            excel_buffer.close()
                            
                        with col3:
                            json_str = df.to_json(orient='records', indent=2)
                            st.download_button(
                                "📥 Download JSON",
                                json_str,
                                f"{source['name']}_data.json",
                                "application/json"
                            )
                    else:
                        st.error("Nu am putut extrage date. Structura paginii ar putea fi diferită.")
                        st.info("💡 Sfat: Verifică URL-ul sau încearcă să adaugi un selector CSS în setările avansate")
                        
                        # Arată preview HTML pentru debugging
                        with st.expander("🔍 Vezi structura HTML (pentru debugging)"):
                            st.code(soup.prettify()[:5000], language='html')
                
                except requests.exceptions.RequestException as e:
                    st.error(f"Eroare la accesarea URL-ului: {str(e)}")
                except Exception as e:
                    st.error(f"Eroare: {str(e)}")

with tab3:
    st.header("ℹ️ Cum să folosești aplicația")
    
    st.markdown("""
    ### 📝 Pași:
    
    1. **Adaugă o sursă**
       - Mergi la tab-ul "Adaugă Sursă"
       - Completează numele loteriei și URL-ul complet
       - Alege tipul și configurează parametrii
       - Salvează sursa
    
    2. **Extrage date**
       - Mergi la tab-ul "Extrage Date"
       - Alege sursa din listă
       - Specifică câte runde vrei să extragi
       - Apasă "Extrage Date"
    
    3. **Download**
       - Descarcă datele în format CSV, Excel sau JSON
    
    ### 🎯 Exemple de surse:
    
    - **Cehia Keno**: https://www.fortunacr.cz/statistiky
    - **Loto România**: https://www.loto.ro/rezultate-loto
    - **Euro Jackpot**: https://www.euro-jackpot.net/ro/rezultate
    
    ### ⚠️ Note:
    
    - Unele site-uri pot avea protecție anti-scraping
    - Structura HTML diferă de la site la site
    - Pentru rezultate optime, verifică că URL-ul afișează rezultatele direct
    - Folosește setările avansate pentru site-uri complexe
    
    ### 🔧 Setări Avansate:
    
    Dacă aplicația nu găsește automat datele:
    - Deschide site-ul în browser
    - Click dreapta pe tabelul cu rezultate → "Inspect"
    - Caută class sau id-ul containerului (ex: `.results-table`)
    - Adaugă acest selector în setările avansate
    """)
    
    st.divider()
    
    st.markdown("""
    ### 📦 Instalare pentru GitHub:
    
    Creează fișierul `requirements.txt`:
    ```
    streamlit
    requests
    beautifulsoup4
    pandas
    openpyxl
    lxml
    selenium
    webdriver-manager
    ```
    
    **Pentru Selenium (click automat pe butoane):**
    ```bash
    # Instalează Chrome Driver automat
    pip install webdriver-manager
    ```
    
    Rulează local:
    ```bash
    streamlit run app.py
    ```
    """)

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    🎰 Lottery Data Extractor v1.0 | Made with Streamlit
</div>
""", unsafe_allow_html=True)
