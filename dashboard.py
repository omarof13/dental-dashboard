import streamlit as st
import pandas as pd
import requests

API_URL = "https://jalal-bot-qc.azurewebsites.net"

st.set_page_config(page_title="Dental Bot Dashboard", layout="wide", page_icon="🦷")

st.title("🦷 Gestion des Rendez-vous")
st.markdown(f"**Connecté à :** `{API_URL}`")

# --- BOUTON DE SUPPRESSION (DANGER ZONE) ---
with st.expander("🚨 Zone de Danger (Suppression)"):
    st.write("Attention, cette action est irréversible.")
    if st.button("🗑️ SUPPRIMER TOUS LES ENREGISTREMENTS", type="primary"):
        try:
            res = requests.delete(f"{API_URL}/bookings")
            if res.status_code == 200:
                st.success("Base de données effacée avec succès !")
                st.rerun()
            else:
                st.error("Erreur lors de la suppression.")
        except Exception as e:
            st.error(f"Erreur technique : {e}")

if st.button("🔄 Rafraîchir les données"):
    st.rerun()

try:
    response = requests.get(f"{API_URL}/bookings", timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        
        if data:
            df = pd.DataFrame(data)
            
            if "first_name" in df.columns and "last_name" in df.columns:
                df["Full Name"] = df["first_name"] + " " + df["last_name"]
            else:
                df["Full Name"] = "Inconnu"

            # AJOUT DE LA COLONNE 'call_duration'
            display_cols = [
                "Full Name", "phone", "email", "service", 
                "appointment_date", "time_preference", 
                "call_duration",  # <--- NOUVELLE COLONNE
                "source", "created_at"
            ]
            
            final_cols = [c for c in display_cols if c in df.columns]
            
            st.dataframe(df[final_cols], use_container_width=True)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total RDV", len(df))
            
            if "is_new_patient" in df.columns:
                new_patients = df[df["is_new_patient"].str.lower() == "yes"].shape[0]
                col2.metric("Nouveaux Patients", new_patients)
            
            if "call_duration" in df.columns:
                # Calcul rapide de la moyenne de durée (si possible)
                # On convertit "2:30" en secondes pour la moyenne
                try:
                    def to_seconds(t_str):
                        if not t_str or ":" not in str(t_str): return 0
                        m, s = map(int, t_str.split(":"))
                        return m * 60 + s
                    
                    avg_sec = df["call_duration"].apply(to_seconds).mean()
                    avg_min = int(avg_sec // 60)
                    avg_remain_sec = int(avg_sec % 60)
                    col3.metric("Durée Moyenne Appel", f"{avg_min}:{avg_remain_sec:02d}")
                except:
                    col3.metric("Durée Moyenne", "N/A")

        else:
            st.info("📭 Aucun rendez-vous.")
            
    else:
        st.error(f"Erreur API ({response.status_code})")
        
except Exception as e:
    st.error(f"❌ Erreur de connexion : {e}")
