@echo off
title runCtaTrading
echo runCtaTrading
start cmd /k "cd CtaTrading && python runCtaTrading.py"
start cmd /k "cd DataRecording && python runDataRecording.py"