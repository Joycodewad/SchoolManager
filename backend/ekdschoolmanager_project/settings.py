import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "development-only-secret-key")
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "DJANGO_ALLOWED_HOSTS",
        "localhost,127.0.0.1,arielfx.groupezenith.net"
    ).split(",")
    if host.strip()
]

# En développement, l'application mobile joint le serveur par une autre adresse
# que « localhost » : 10.0.2.2 depuis l'émulateur Android (alias de la machine
# hôte), et l'IP du poste sur le réseau local depuis un téléphone réel. Sans
# ces entrées, Django refuse la requête avec « Invalid HTTP_HOST header ».
#
# Ouvert seulement quand DEBUG est actif : en production, la liste reste celle
# de la configuration, et l'API doit de toute façon être servie en HTTPS.
if DEBUG:
    ALLOWED_HOSTS += [
        host for host in ("10.0.2.2", "0.0.0.0") if host not in ALLOWED_HOSTS
    ]
    # Les IP privées du poste changent d'un réseau à l'autre : les découvrir
    # évite d'éditer la configuration à chaque changement de Wi-Fi.
    try:
        import socket

        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = info[4][0]
            if address not in ALLOWED_HOSTS:
                ALLOWED_HOSTS.append(address)
    except OSError:
        # Machine sans résolution de son propre nom : on s'en passe, les
        # adresses fixes ci-dessus suffisent à l'émulateur.
        pass

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "ekdschoolmanager",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ekdschoolmanager_project.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "ekdschoolmanager_project.wsgi.application"
ASGI_APPLICATION = "ekdschoolmanager_project.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "ekdschoolmanager"),
        "USER": os.getenv("POSTGRES_USER", "kadjr01"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "OPTIONS": {"connect_timeout": 10},
    }
}

AUTH_PASSWORD_VALIDATORS = []
AUTH_USER_MODEL = "ekdschoolmanager.CustomUser"
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "America/New_York"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "https://arielfx.groupezenith.net",
]
CSRF_TRUSTED_ORIGINS = [
    "https://arielfx.groupezenith.net",
]
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
}

from corsheaders.defaults import default_headers
CORS_ALLOW_HEADERS = (*default_headers, "x-school-id", "x-academic-year-id")
# Le front tourne sur un autre port que l'API : sans cette liste, le navigateur
# masque l'en-tête au JavaScript et tous les PDF se téléchargent sous le nom de
# repli, sans la session ni la classe. Concerne bulletins et emplois du temps.
CORS_EXPOSE_HEADERS = ["Content-Disposition"]
