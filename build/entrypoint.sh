#!/usr/bin/env bash

if [[ -z "$GPU-BURST" ]] ; then
  echo "$GPU-BURST"
fi

if [ ! -f "$OPENSHIFT-PSAP-CI" ] ; then
  echo "$OPENSHIFT-PSAP-CI"  
fi

exec bash
