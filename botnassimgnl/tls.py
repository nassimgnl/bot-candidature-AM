"""Contexte TLS partage par SMTP et IMAP.

Le Python de python.org sur Mac n'installe pas les certificats racines : sans certifi,
la connexion a Gmail echoue avec CERTIFICATE_VERIFY_FAILED.
"""

import ssl

import certifi


def secure_context() -> ssl.SSLContext:
    """Contexte TLS qui verifie les certificats avec la liste a jour de certifi."""
    return ssl.create_default_context(cafile=certifi.where())
