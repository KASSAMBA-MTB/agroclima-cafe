# =============================================================================
# Django settings for agroclima project.
# Configuração saneada: nenhuma credencial real deve permanecer neste arquivo.
# =============================================================================

from pathlib import Path
import os

from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


# =============================================================================
# Segurança
# =============================================================================

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

if not SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY não configurada. "
        "Defina a variável de ambiente antes de iniciar o Django."
    )

DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() in ("1", "true", "yes")

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]


# =============================================================================
# Application definition
# =============================================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "usuarios",
    "municipios",
    "clima",
    "geadas",
    "dashboard",
    "relatorios",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "agroclima.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "agroclima.wsgi.application"


# =============================================================================
# PostgreSQL
# PostgreSQL é a única persistência oficial do projeto.
# Nenhuma senha ou credencial é armazenada no código.
# =============================================================================

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5432")

_missing_db = [
    name
    for name, value in {
        "DB_NAME": DB_NAME,
        "DB_USER": DB_USER,
        "DB_PASSWORD": DB_PASSWORD,
    }.items()
    if not value
]

if _missing_db:
    raise ImproperlyConfigured(
        "Variáveis PostgreSQL ausentes: " + ", ".join(_missing_db)
    )

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": DB_NAME,
        "USER": DB_USER,
        "PASSWORD": DB_PASSWORD,
        "HOST": DB_HOST,
        "PORT": DB_PORT,
    }
}


# =============================================================================
# Password validation
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# =============================================================================
# Internationalization
# =============================================================================

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True


# =============================================================================
# Static files
# =============================================================================

STATIC_URL = "static/"

STATICFILES_DIRS = [
    BASE_DIR / "static"
]

STATIC_ROOT = BASE_DIR / "staticfiles"


# =============================================================================
# AGROCLIMA CAFÉ
# CONFIGURAÇÃO MUNICIPAL DO BALANÇO HÍDRICO — FASE 6.2
# =============================================================================
#
# Esta seção ativa a configuração explicitamente no backend.
#
# IMPORTANTE:
# - os valores não são defaults do HydricBalanceService;
# - cada município possui uma entrada explícita;
# - CAD = 100 mm é uma referência metodológica documentada para
#   balanços hídricos de cafeeiros, não um valor criado pelo código;
# - a referência utilizada é literatura técnica da Embrapa sobre
#   balanço hídrico do cafeeiro;
# - o armazenamento inicial de 100 mm representa a condição explícita
#   de início em capacidade de campo para esta série de referência;
# - esta configuração é uma hipótese metodológica de referência,
#   não uma caracterização físico-hídrica individual de cada talhão;
# - eventual substituição por CAD derivada de solo/localidade deverá
#   preservar a proveniência e ser feita em etapa metodológica própria.
#
# Fonte metodológica:
# Embrapa — Fenologia do Cafeeiro: Condições Agrometeorológicas e
# Balanço Hídrico. O documento informa CAD de 100 mm para representar
# a maioria dos solos das principais regiões cafeeiras e relaciona a
# CAD às propriedades físico-hídricas do solo e à profundidade efetiva
# das raízes.
#
# A aplicação atualmente fornece ao serviço a chave municipal pelo
# nome normalizado do município. Por isso, as chaves abaixo reproduzem
# exatamente os nomes usados pelo fluxo DashboardService.
#
# Códigos IBGE de referência territorial:
# Águas da Prata             3500402
# Andradas                   3102605
# Espírito Santo do Pinhal   3515186
# Poços de Caldas            3151800
# São João da Boa Vista      3549102
# Vargem Grande do Sul       3556404
#
# =============================================================================

AGROCLIMA_HYDRIC_BALANCE_CONFIG = {
    "Águas da Prata": {
        "cad_mm": 100.0,
        "cad_provenance": {
            "source": "Embrapa",
            "reference": (
                "Fenologia do Cafeeiro: Condições Agrometeorológicas "
                "e Balanço Hídrico"
            ),
            "basis": (
                "CAD de referência de 100 mm para balanços hídricos "
                "do cafeeiro, conforme literatura técnica citada."
            ),
            "municipality_specific": False,
            "methodological_status": "REFERENCE_ASSUMPTION",
        },
        "initial_arm_mm": 100.0,
        "initial_arm_method": "EXPLICIT",
    },

    "Andradas": {
        "cad_mm": 100.0,
        "cad_provenance": {
            "source": "Embrapa",
            "reference": (
                "Fenologia do Cafeeiro: Condições Agrometeorológicas "
                "e Balanço Hídrico"
            ),
            "basis": (
                "CAD de referência de 100 mm para balanços hídricos "
                "do cafeeiro, conforme literatura técnica citada."
            ),
            "municipality_specific": False,
            "methodological_status": "REFERENCE_ASSUMPTION",
        },
        "initial_arm_mm": 100.0,
        "initial_arm_method": "EXPLICIT",
    },

    "Espírito Santo do Pinhal": {
        "cad_mm": 100.0,
        "cad_provenance": {
            "source": "Embrapa",
            "reference": (
                "Fenologia do Cafeeiro: Condições Agrometeorológicas "
                "e Balanço Hídrico"
            ),
            "basis": (
                "CAD de referência de 100 mm para balanços hídricos "
                "do cafeeiro, conforme literatura técnica citada."
            ),
            "municipality_specific": False,
            "methodological_status": "REFERENCE_ASSUMPTION",
        },
        "initial_arm_mm": 100.0,
        "initial_arm_method": "EXPLICIT",
    },

    "Poços de Caldas": {
        "cad_mm": 100.0,
        "cad_provenance": {
            "source": "Embrapa",
            "reference": (
                "Fenologia do Cafeeiro: Condições Agrometeorológicas "
                "e Balanço Hídrico"
            ),
            "basis": (
                "CAD de referência de 100 mm para balanços hídricos "
                "do cafeeiro, conforme literatura técnica citada."
            ),
            "municipality_specific": False,
            "methodological_status": "REFERENCE_ASSUMPTION",
        },
        "initial_arm_mm": 100.0,
        "initial_arm_method": "EXPLICIT",
    },

    "São João da Boa Vista": {
        "cad_mm": 100.0,
        "cad_provenance": {
            "source": "Embrapa",
            "reference": (
                "Fenologia do Cafeeiro: Condições Agrometeorológicas "
                "e Balanço Hídrico"
            ),
            "basis": (
                "CAD de referência de 100 mm para balanços hídricos "
                "do cafeeiro, conforme literatura técnica citada."
            ),
            "municipality_specific": False,
            "methodological_status": "REFERENCE_ASSUMPTION",
        },
        "initial_arm_mm": 100.0,
        "initial_arm_method": "EXPLICIT",
    },

    "Vargem Grande do Sul": {
        "cad_mm": 100.0,
        "cad_provenance": {
            "source": "Embrapa",
            "reference": (
                "Fenologia do Cafeeiro: Condições Agrometeorológicas "
                "e Balanço Hídrico"
            ),
            "basis": (
                "CAD de referência de 100 mm para balanços hídricos "
                "do cafeeiro, conforme literatura técnica citada."
            ),
            "municipality_specific": False,
            "methodological_status": "REFERENCE_ASSUMPTION",
        },
        "initial_arm_mm": 100.0,
        "initial_arm_method": "EXPLICIT",
    },
}


# =============================================================================
# FIM DA CONFIGURAÇÃO MUNICIPAL DO BALANÇO HÍDRICO
# =============================================================================
#
# A configuração acima é consumida exclusivamente por
# HydricBalanceConfigurationService.
#
# Nenhum cálculo de balanço é realizado neste arquivo.
# Nenhum indicador é calculado no frontend.
# =============================================================================
