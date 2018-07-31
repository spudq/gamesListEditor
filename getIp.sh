#!/bin/bash
ip route get 8.8.8.8 2>/dev/null | awk '{print $NF; exit}'
