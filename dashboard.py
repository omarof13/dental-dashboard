import streamlit as st
import pandas as pd
import requests
import streamlit.components.v1 as components

# URL de votre API
# IMPORTANT: Pour le WebRTC, il faut utiliser wss:// si https, ou ws:// si http
API_URL = "https://jalal-bot-qc.azurewebsites.net" 
WS_URL = API_URL.replace("https://", "wss://").replace("http://", "ws://")

st.set_page_config(page_title="Dental Bot Dashboard", layout="wide", page_icon="🦷")

st.title("🦷 Gestion de Clinique Dentaire")

# --- TABS ---
tab1, tab2 = st.tabs(["📊 Dashboard RDV", "📞 Web Call (Test)"])

# ==========================================
# TAB 1: DASHBOARD (ADMIN)
# ==========================================
with tab1:
    col_header_1, col_header_2 = st.columns([3, 1])
    with col_header_1:
        st.markdown(f"**Status API:** Connecté à `{API_URL}`")
    with col_header_2:
        if st.button("🔄 Rafraîchir les données", key="refresh", use_container_width=True):
            st.rerun()

    # --- LISTE DES RENDEZ-VOUS ---
    try:
        response = requests.get(f"{API_URL}/bookings", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data:
                df = pd.DataFrame(data)
                
                # Création colonne Nom Complet
                if "first_name" in df.columns and "last_name" in df.columns:
                    df["Full Name"] = df["first_name"] + " " + df["last_name"]
                else:
                    df["Full Name"] = "Inconnu"

                # Colonnes à afficher
                display_cols = ["Full Name", "phone", "email", "service", "appointment_date", "time_preference", "source", "created_at"]
                final_cols = [c for c in display_cols if c in df.columns]
                
                st.dataframe(df[final_cols], use_container_width=True)
                
                st.divider()
                
                # --- ZONE DANGER (SUPPRIMER TOUT) ---
                st.subheader("🗑️ Zone de Danger")
                col_del_1, col_del_2 = st.columns([3, 1])
                with col_del_1:
                    st.warning("Attention, cette action supprimera définitivement tous les rendez-vous de la base de données.")
                with col_del_2:
                    if st.button("🚨 SUPPRIMER TOUT", type="primary", use_container_width=True):
                        try:
                            del_res = requests.delete(f"{API_URL}/bookings", timeout=10)
                            if del_res.status_code == 200:
                                st.success("Base de données vidée !")
                                st.rerun()
                            else:
                                st.error("Erreur lors de la suppression.")
                        except Exception as e:
                            st.error(f"Erreur: {e}")

            else:
                st.info("📭 Aucun rendez-vous pour le moment.")
                # Même si vide, on peut vouloir nettoyer
                if st.button("Nettoyer la base (même si vide)", type="secondary"):
                     requests.delete(f"{API_URL}/bookings")
                     st.rerun()
        else:
            st.error(f"Erreur API ({response.status_code})")

    except Exception as e:
        st.error(f"Erreur de connexion : {e}")


# ==========================================
# TAB 2: WEB CALL CLIENT (TEST)
# ==========================================
with tab2:
    st.header("Test de l'Agent Vocal (Web)")
    st.caption("Ce module utilise votre microphone pour parler directement à Sarah via WebSocket.")

    # LE SCRIPT JS POUR L'APPEL
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: sans-serif; text-align: center; color: #333; }}
            .container {{ display: flex; flex-direction: column; align-items: center; gap: 20px; margin-top: 30px; }}
            .btn-group {{ display: flex; gap: 20px; flex-wrap: wrap; justify-content: center; }}
            button {{
                padding: 15px 30px; font-size: 16px; border: none; border-radius: 50px; cursor: pointer;
                transition: transform 0.1s; box-shadow: 0 4px 6px rgba(0,0,0,0.1); font-weight: bold;
            }}
            button:active {{ transform: scale(0.95); }}
            .btn-fr {{ background-color: #4CAF50; color: white; }}
            .btn-en {{ background-color: #2196F3; color: white; }}
            .btn-hangup {{ background-color: #f44336; color: white; display: none; }}
            
            .status {{ font-weight: bold; margin-top: 10px; font-size: 18px; min-height: 25px; color: #555; }}
            
            /* Animation d'appel */
            .pulse {{
                width: 80px; height: 80px; background: #f44336; border-radius: 50%;
                display: none; align-items: center; justify-content: center; color: white;
                font-size: 30px; animation: pulse-animation 1.5s infinite;
            }}
            @keyframes pulse-animation {{
                0% {{ box-shadow: 0 0 0 0 rgba(244, 67, 54, 0.7); }}
                70% {{ box-shadow: 0 0 0 15px rgba(244, 67, 54, 0); }}
                100% {{ box-shadow: 0 0 0 0 rgba(244, 67, 54, 0); }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div id="status" class="status">Prêt à appeler</div>
            
            <div id="pulse" class="pulse">📞</div>

            <div id="controls" class="btn-group">
                <button class="btn-fr" onclick="startCall('fr')">Appeler (Français) 🇫🇷</button>
                <button class="btn-en" onclick="startCall('en')">Call (English) 🇺🇸</button>
            </div>
            
            <button id="hangupBtn" class="btn-hangup" onclick="endCall()">Raccrocher / Hang Up</button>
        </div>

        <script>
            let socket;
            let audioContext;
            let processor;
            let source;
            let nextStartTime = 0;

            const WS_BASE_URL = "{WS_URL}";

            function floatTo16BitPCM(input) {{
                let output = new Int16Array(input.length);
                for (let i = 0; i < input.length; i++) {{
                    let s = Math.max(-1, Math.min(1, input[i]));
                    output[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                }}
                return output;
            }}

            async function startCall(lang) {{
                document.getElementById('status').innerText = "Connexion...";
                
                try {{
                    audioContext = new (window.AudioContext || window.webkitAudioContext)({{ sampleRate: 24000 }});
                    socket = new WebSocket(WS_BASE_URL + "/ws/web/" + lang);
                    
                    socket.onopen = async () => {{
                        document.getElementById('status').innerText = "📞 En ligne (" + lang.toUpperCase() + ")";
                        toggleUI(true);
                        
                        const stream = await navigator.mediaDevices.getUserMedia({{ audio: {{ channelCount: 1, sampleRate: 24000 }} }});
                        source = audioContext.createMediaStreamSource(stream);
                        processor = audioContext.createScriptProcessor(4096, 1, 1);
                        
                        processor.onaudioprocess = (e) => {{
                            if (socket.readyState === WebSocket.OPEN) {{
                                const inputData = e.inputBuffer.getChannelData(0);
                                const pcmData = floatTo16BitPCM(inputData);
                                const base64String = btoa(String.fromCharCode(...new Uint8Array(pcmData.buffer)));
                                socket.send(JSON.stringify({{ event: "media", media: base64String }}));
                            }}
                        }};

                        source.connect(processor);
                        processor.connect(audioContext.destination);
                    }};

                    socket.onmessage = async (event) => {{
                        const data = JSON.parse(event.data);
                        if (data.event === "media") {{
                            playAudio(data.media);
                        }} else if (data.event === "hangup") {{
                            endCall();
                        }}
                    }};

                    socket.onclose = () => {{ endCall(); }};

                }} catch (err) {{
                    console.error(err);
                    document.getElementById('status').innerText = "Erreur Micro ou Connexion";
                }}
            }}

            function playAudio(base64Data) {{
                const binaryString = atob(base64Data);
                const len = binaryString.length;
                const bytes = new Uint8Array(len);
                for (let i = 0; i < len; i++) {{ bytes[i] = binaryString.charCodeAt(i); }}
                const int16Data = new Int16Array(bytes.buffer);
                const floatData = new Float32Array(int16Data.length);
                for (let i = 0; i < int16Data.length; i++) {{ floatData[i] = int16Data[i] / 32768.0; }}

                const buffer = audioContext.createBuffer(1, floatData.length, 24000);
                buffer.getChannelData(0).set(floatData);

                const source = audioContext.createBufferSource();
                source.buffer = buffer;
                source.connect(audioContext.destination);
                
                const currentTime = audioContext.currentTime;
                if (nextStartTime < currentTime) nextStartTime = currentTime;
                source.start(nextStartTime);
                nextStartTime += buffer.duration;
            }}

            function endCall() {{
                if (socket) socket.close();
                if (processor) {{ processor.disconnect(); processor = null; }}
                if (source) {{ source.disconnect(); source = null; }}
                if (audioContext) {{ audioContext.close(); }}
                document.getElementById('status').innerText = "Appel terminé.";
                toggleUI(false);
            }}

            function toggleUI(inCall) {{
                document.getElementById('controls').style.display = inCall ? 'none' : 'flex';
                document.getElementById('hangupBtn').style.display = inCall ? 'block' : 'none';
                document.getElementById('pulse').style.display = inCall ? 'flex' : 'none';
            }}
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=450)
