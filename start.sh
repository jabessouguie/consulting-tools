#!/bin/bash

# 🚀 Script de démarrage - WEnvision Consulting Tools
# Fix pour Python 3.14 + lxml sur macOS

# Export library paths pour lxml
export DYLD_LIBRARY_PATH=/opt/homebrew/opt/libxml2/lib:/opt/homebrew/opt/libxslt/lib:/usr/lib:$DYLD_LIBRARY_PATH

# Démarrer l'application
python3 app.py "$@"
