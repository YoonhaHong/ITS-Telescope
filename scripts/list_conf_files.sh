#!/bin/bash

# 지정된 디렉토리
dir=~/Telescope/configs/kek-2MOSS_thr_scan

# 디렉토리 내부의 모든 파일들의 절대 경로를 순서대로 구하고, 쉼표로 구분하여 출력
find "$dir" -type f | sort | tr '\n' ',' | sed 's/,$//'

