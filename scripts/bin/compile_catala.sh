#!/bin/bash
set -e

# Compile LISR
echo "Compiling LISR..."
catala Python engines/catala/lisr.catala_en -o engines/catala/lisr_catala.py
echo "Done."
