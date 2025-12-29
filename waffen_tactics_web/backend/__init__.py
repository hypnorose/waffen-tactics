"""Compatibility shim package to allow tests to import
`waffen_tactics_web.backend` while the real backend code lives in the
`waffen-tactics-web/backend` directory (dash in name). This file adds the
actual backend folder to the package `__path__` so normal imports work in CI.
"""
import os

# Compute absolute path to the real backend folder
HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, '..'))
REAL_BACKEND = os.path.abspath(os.path.join(ROOT, '..', 'waffen-tactics-web', 'backend'))

if os.path.isdir(REAL_BACKEND) and REAL_BACKEND not in __path__:
    __path__.insert(0, REAL_BACKEND)
