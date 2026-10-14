#!/bin/bash
cd "$1"
tar --exclude='.env*' --exclude='*.pem' --exclude='app/.git' -czpf backup.tar.gz app
