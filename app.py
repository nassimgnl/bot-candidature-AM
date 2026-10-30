"""Lance BOT nassimgnl : python app.py puis http://localhost:5000"""

import os

from dotenv import load_dotenv

load_dotenv()

from botnassimgnl import create_app  # noqa: E402  (le .env doit etre charge avant)

DEFAULT_PORT = 5000

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", DEFAULT_PORT))
    print(f"\n  ➜  BOT nassimgnl : http://localhost:{port}\n")
    # 127.0.0.1 : le site n'est accessible que depuis ton ordinateur.
    app.run(host="127.0.0.1", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
