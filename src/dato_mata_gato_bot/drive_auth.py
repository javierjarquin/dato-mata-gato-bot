"""Autenticación OAuth con Google Drive -- una sola autorización manual
(navegador) y listo para siempre: el refresh token queda guardado en
credentials/google_drive_token.json y se renueva solo, sin volver a pedir
login.

Corré esto UNA VEZ antes de que el pipeline suba nada:
    python -m dato_mata_gato_bot.drive_auth
"""

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scope amplio (no drive.file): la carpeta destino la crea el usuario a mano
# en la UI de Drive, no esta app -- drive.file solo da acceso a archivos que
# la propia app creó o que el usuario abrió vía Picker, y no alcanzaría para
# escribir en una carpeta preexistente dada solo por su ID.
SCOPES = ["https://www.googleapis.com/auth/drive"]

CREDENTIALS_DIR = Path(__file__).resolve().parent.parent.parent / "credentials"
CLIENT_SECRET_PATH = CREDENTIALS_DIR / "google_drive_client_secret.json"
TOKEN_PATH = CREDENTIALS_DIR / "google_drive_token.json"


def _load_credentials() -> Credentials | None:
    if not TOKEN_PATH.exists():
        return None
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return creds


def authorize_interactive() -> None:
    """Autoriza la cuenta de Google y guarda el refresh token. Se corre
    una sola vez, a mano. No intenta abrir el navegador solo (evita
    ambigüedad sobre qué pestaña es la correcta si hay varias abiertas) --
    imprime la URL exacta para abrir manualmente."""
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_PATH), SCOPES)
    creds = flow.run_local_server(port=0, open_browser=False)
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")


def get_drive_service():
    creds = _load_credentials()
    if creds is None or not creds.valid:
        raise RuntimeError(
            "No hay autorización de Google Drive todavía (o expiró sin refresh "
            "token válido). Corré: python -m dato_mata_gato_bot.drive_auth"
        )
    return build("drive", "v3", credentials=creds)


if __name__ == "__main__":
    authorize_interactive()
    print(f"Autorización guardada en {TOKEN_PATH}")
