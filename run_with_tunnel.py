import time
from pyngrok import ngrok

# Добавьте ваш токен сюда (или выполните: ngrok config add-authtoken YOUR_TOKEN)
NGROK_AUTHTOKEN = "3BrngeAbmHGC8uwkqbK40cy2HKr_8seNUHg3S2dyPq2QQ5H1"  # Вставьте токен сюда

def main():
    if NGROK_AUTHTOKEN:
        ngrok.set_auth_token(NGROK_AUTHTOKEN)
    
    print("Starting ngrok tunnel...")
    public_url = ngrok.connect(3000)
    print(f"\n{'='*60}")
    print(f"Frontend URL: {public_url}")
    print(f"{'='*60}\n")
    print("Update your .env with this URL, then restart frontend.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        ngrok.kill()

if __name__ == "__main__":
    main()
