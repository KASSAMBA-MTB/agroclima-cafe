# =============================================================================
# Django settings for agroclima project.
# Configuracao saneada: nenhuma credencial real deve permanecer neste arquivo.
# =============================================================================

from pathlib import Path
import os

from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


# =============================================================================
# Seguranca
# =============================================================================

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

if not SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY nao configurada. "
        "Defina a variavel de ambiente antes de iniciar o Django."
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
    "core.intelligence.apps.IntelligenceConfig",
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
# PostgreSQL e a unica persistencia oficial do projeto.
# Nenhuma senha ou credencial e armazenada no codigo.
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
        "Variaveis PostgreSQL ausentes: " + ", ".join(_missing_db)
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
# AGROCLIMA CAFE
# CONFIGURACAO MUNICIPAL DO BALANCO HIDRICO — FASE 6.2
# =============================================================================

# Esta secao ativa a configuracao explicitamente no backend.
#
# IMPORTANTE:
# - os valores nao sao defaults do HydricBalanceService;
# - cada municipio possui uma entrada explicita;
# - CAD = 100 mm e uma referencia metodologica documentada para
#   balancos hidricos de cafeeiros, nao um valor criado pelo codigo;
# - a referencia utilizada e literatura tecnica da Embrapa sobre
#   balanco hidrico do cafeeiro;
# - o armazenamento inicial de 100 mm representa a condicao explicita
#   de inicio em capacidade de campo para esta serie de referencia;
# - esta configuracao e uma hipotese metodologica de referencia,
#   nao uma caracterizacao fisico-hidrica individual de cada talhao;
# - eventual substituicao por CAD derivada de solo/localidade devera
#   preservar a proveniencia e ser feita em etapa metodologica propria.

# Fonte metodologica:
# Embrapa — Fenologia do Cafeeiro: Condicoes Agrometeorologicas e
# Balanco Hidrico. O documento informa CAD de 100 mm para representar
# a maioria dos solos das principais regioes cafeeiras e relaciona a
# CAD as propriedades fisico-hidricas do solo e a profundidade efetiva
# das raizes.

# A aplicacao atualmente fornece ao servico a chave municipal pelo
# nome normalizado do municipio. Por isso, as chaves abaixo reproduzem
# exatamente os nomes usados pelo fluxo DashboardService.

# Codigos IBGE de referencia territorial:
# Aguas da Prata             3500402
# Andradas                   3102605
# Espirito Santo do Pinhal   3515186
# Pocos de Caldas            3151800
# Sao Joao da Boa Vista      3549102
# Vargem Grande do Sul       3556404

# =============================================================================

AGROCLIMA_HYDRIC_BALANCE_CONFIG = {
    "Águas da Prata": {
        "cad_mm": 100.0,
        "cad_provenance": {
            "source": "Embrapa",
            "reference": (
                "Fenologia do Cafeeiro: Condicoes Agrometeorologicas "
                "e Balanco Hidrico"
            ),
            "basis": (
                "CAD de referencia de 100 mm para balancos hidricos "
                "do cafeeiro, conforme literatura tecnica citada."
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
                "Fenologia do Cafeeiro: Condicoes Agrometeorologicas "
                "e Balanco Hidrico"
            ),
            "basis": (
                "CAD de referencia de 100 mm para balancos hidricos "
                "do cafeeiro, conforme literatura tecnica citada."
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
                "Fenologia do Cafeeiro: Condicoes Agrometeorologicas "
                "e Balanco Hidrico"
            ),
            "basis": (
                "CAD de referencia de 100 mm para balancos hidricos "
                "do cafeeiro, conforme literatura tecnica citada."
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
                "Fenologia do Cafeeiro: Condicoes Agrometeorologicas "
                "e Balanco Hidrico"
            ),
            "basis": (
                "CAD de referencia de 100 mm para balancos hidricos "
                "do cafeeiro, conforme literatura tecnica citada."
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
                "Fenologia do Cafeeiro: Condicoes Agrometeorologicas "
                "e Balanco Hidrico"
            ),
            "basis": (
                "CAD de referencia de 100 mm para balancos hidricos "
                "do cafeeiro, conforme literatura tecnica citada."
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
                "Fenologia do Cafeeiro: Condicoes Agrometeorologicas "
                "e Balanco Hidrico"
            ),
            "basis": (
                "CAD de referencia de 100 mm para balancos hidricos "
                "do cafeeiro, conforme literatura tecnica citada."
            ),
            "municipality_specific": False,
            "methodological_status": "REFERENCE_ASSUMPTION",
        },
        "initial_arm_mm": 100.0,
        "initial_arm_method": "EXPLICIT",
    },
}


# =============================================================================
# FIM DA CONFIGURACAO MUNICIPAL DO BALANCO HIDRICO
# =============================================================================

# A configuracao acima e consumida exclusivamente por
# HydricBalanceConfigurationService.
#
# Nenhum calculo de balanco e realizado neste arquivo.
# Nenhum indicador e calculado no frontend.
# =============================================================================
