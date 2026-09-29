#!/usr/bin/env bash
P=/home/saini/theme5/fdb-env/lib/python3.10/site-packages/typesafe_sdk
grep -nE 'class ChoiceAnswer|class SystemOneResponse|class Answer' -A 14 $P/_core/response_types.py | head -60
echo "--- probability fields:"; grep -rnE 'probab|logprob|distribution|confidence' $P | head -8
