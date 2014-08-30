#!/bin/bash

cd ..
${PYTHON:-python3} setup_mac.py py2app $@
cd scripts
./fixup-app.sh



