import os
import urllib.request

# Dossier de destination
EMOJI_DIR = os.path.join("assets", "emojis")
os.makedirs(EMOJI_DIR, exist_ok=True)

# Mappage des émojis et leurs codes hexadécimaux Noto/Twemoji
EMOJIS = {
    "💡": "1f4a1",
    "🔍": "1f50d",
    "⚡": "26a1",
    "🧠": "1f9e0",
    "🤖": "1f916",
    "🛡️": "1f6e1",
    "🌐": "1f310",
    "🔐": "1f510",
    "💻": "1f4bb",
    "🚀": "1f680",
    "📡": "1f4e1",
    "🧬": "1f9ec"
}

# Téléchargement depuis le CDN Twemoji (Twitter / Twemoji PNG Open Source)
BASE_URL = "https://cdn.jsdelivr.net/gh/jdecked/twemoji@latest/assets/72x72/"

for char, hex_code in EMOJIS.items():
    # Gestion des sélecteurs de variation si présent
    clean_hex = hex_code.split("-")[0]
    url = f"{BASE_URL}{hex_code}.png"
    
    # Nom de fichier selon votre préférence (char.png ou hex.png)
    file_path = os.path.join(EMOJI_DIR, f"{char}.png")
    
    try:
        urllib.request.urlretrieve(url, file_path)
        print(f"✅ Téléchargé : {char}.png ({hex_code}.png)")
    except Exception as e:
        # Essai alternatif si le code hex standard comporte une nuance
        alt_url = f"{BASE_URL}{clean_hex}.png"
        try:
            urllib.request.urlretrieve(alt_url, file_path)
            print(f"✅ Téléchargé (fallback) : {char}.png")
        except Exception as err:
            print(f"❌ Échec pour {char} ({hex_code}) : {err}")

print("\n🎉 Téléchargement terminé dans assets/emojis/ !")
