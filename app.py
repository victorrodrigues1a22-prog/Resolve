"""Ponto de entrada da central Resolve. Regras e telas ficam em support/."""
import os
from support import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", port=int(os.environ.get("PORT", "5000")))
