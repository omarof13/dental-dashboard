import streamlit as st
import pandas as pd
import requests

# URL de votre API sur Azure
# C'est ici qu'il va chercher les données
API_URL = "https://jalal-bot-qc.azurewebsites.net"

st.set_page_config(page_title="Dental Bot Dashboard", layout="wide", page_icon="🦷")

st.title("🦷 Gestion des Rendez-vous (Azure Connected)")
st.markdown(f"**Status API:** Connecté à `{API_URL}`")

if st.button("🔄 Rafraîchir les données"):
    st.rerun()

try:
    response = requests.get(f"{API_URL}/bookings", timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        
        if data:
            df = pd.DataFrame(data)
            
            # Organisation des colonnes pour l'affichage
            # On combine Prénom et Nom pour la lisibilité
            if "first_name" in df.columns and "last_name" in df.columns:
                df["Full Name"] = df["first_name"] + " " + df["last_name"]
            else:
                df["Full Name"] = "Inconnu"

            # Sélection des colonnes à afficher
            display_cols = [
                "Full Name", "phone", "email", "service", 
                "is_new_patient", "appointment_date", "time_preference", 
                "source", "created_at"
            ]
            
            # Filtrer les colonnes qui existent vraiment (sécurité)
            final_cols = [c for c in display_cols if c in df.columns]
            
            st.dataframe(df[final_cols], use_container_width=True)
            
            # Statistiques rapides
            col1, col2, col3 = st.columns(3)
            col1.metric("Total RDV", len(df))
            
            # Compter les nouveaux patients
            if "is_new_patient" in df.columns:
                new_patients = df[df["is_new_patient"].str.lower() == "yes"].shape[0]
                col2.metric("Nouveaux Patients", new_patients)
            
            # Service le plus demandé
            if "service" in df.columns and not df.empty:
                top_service = df["service"].mode()[0]
                col3.metric("Service Top", top_service)

        else:
            st.info("📭 Aucun rendez-vous trouvé dans la base de données.")
            
    else:
        st.error(f"Erreur API ({response.status_code}) : Impossible de récupérer les données.")
        
except Exception as e:
    st.error(f"❌ Erreur de connexion : {e}")
    st.warning("Assurez-vous que votre Web App Azure est bien démarrée (jalal-bot-qc).")