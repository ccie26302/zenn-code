#!/bin/bash
mkdir -p ~/.qwen && cp /seed/settings.json /seed/.env ~/.qwen/ && cd /tmp && timeout 120 qwen -p "1+1 は? 数字だけ答えて"
