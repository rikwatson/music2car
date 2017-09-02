#!/bin/bash

ROOT_SOURCE_DIR=$1
ROOT_DEST_DIR=$2
TARGET_FORMAT=$3

# ensure the destination directory structure exists
mkdir -p $ROOT_DEST_DIR

# loop through all files in the source directory
find "${ROOT_SOURCE_DIR}" -type f \( -name "*" \) -print0 | while read -d $'\0' FULL_SOURCE_PATH; do

  # break the source file path down
  DIR=$(dirname "$FULL_SOURCE_PATH")
  FILENAME=$(basename "$FULL_SOURCE_PATH")
  EXTENSION="${FILENAME##*.}"
  FILENAME="${FILENAME%.*}"

  # calculate the destination file path 
  DEST_DIR=${DIR#${ROOT_SOURCE_DIR}}
  FULL_DEST_DIR=${ROOT_DEST_DIR}${DEST_DIR}

  # skip this file if the destination file already exists
  if ls "${FULL_DEST_DIR}/${FILENAME}"* 1> /dev/null 2>&1; then
    echo "skipping ${FILENAME}"
  else
    mkdir -p "${FULL_DEST_DIR}"
    echo "converting ${FILENAME} to ${FULL_DEST_DIR}"

    # Send the file to XLD for conversion. 
    # If conversion fails, we'll copy it over instead
    if ! xld -o "${FULL_DEST_DIR}" "${FULL_SOURCE_PATH}" -f $3; then
      echo "XLD could not convert ${FULL_SOURCE_PATH} - Coyping instead"
      cp "${FULL_SOURCE_PATH}" "${FULL_DEST_DIR}"
    fi
  fi

done