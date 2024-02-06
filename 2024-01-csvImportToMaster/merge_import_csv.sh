#!/bin/bash
# Purpose: Script to import csv files to master file
# Read the parameters from supplied param.json in the command line
# Iterate over each source CSV file in the specified folder.
# Append the records to the master file after removing the specified columns.
# This code is auto-generated

# Check if a file name is provided as input
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 param_file.json"
    exit 1
fi

# Assign the first argument to a variable
param_file="$1"

# Check if the file exists
if [ ! -f "$param_file" ]; then
    echo "Error: File '$param_file' not found!"
    exit 1
fi

# Read parameters from the specified file
params=$(jq '.' "$param_file")

masterFilePath=$(jq -r '.masterFilePath' <<< "$params")
sourceFileFolder=$(jq -r '.SourceFileFolderLocation' <<< "$params")
delimiter=$(jq -r '.SourceFileDelimiter' <<< "$params")
sourceColumns=$(jq -r '.sourceFileColumnsList' <<< "$params")
removeColumns=$(jq -r '.columnsToRemoveFromSourceFileList' <<< "$params")
outputFile=$(jq -r '.OutputFileName' <<< "$params")
includeLineage=$(jq -r '.includeLineage' <<< "$params")

# Function to remove columns
remove_columns() {
    local file=$1
    local columnsToRemove=$2
    local delimiter=$3

    awk -v cols="$columnsToRemove" -v delim="$delimiter" 'BEGIN{FS=OFS=delim; split(cols, colsToRemoveArr)}
    NR==1 {
        for (i=1; i<=NF; i++) {
            if (index(cols, $i) == 0) {
                printf "%s%s", sep, $i
                sep=OFS
                columnIndices[i]
            }
        }
        print ""
    }
    NR>1 {
        sep=""
        for (i=1; i<=NF; i++) {
            if (i in columnIndices) {
                printf "%s%s", sep, $i
                sep=OFS
            }
        }
        print ""
    }' $file
}


# Function to add lineage columns
add_lineage() {
    local file=$1
    local sourceFileName=$2
    local delimiter=$3
    local dateCreated=$(date "+%Y-%m-%d")

    awk -v date="$dateCreated" -v sourceFile="$sourceFileName" -v delim="$delimiter" 'BEGIN{FS=OFS=delim}
    NR==1 {print $0, "Date Created", "Source File Name"}
    NR>1 {print $0, date, sourceFile}' $file
}

# Check if jq is installed
if ! command -v jq &> /dev/null
then
    echo "jq could not be found, please install it to run this script."
    exit
fi

# Overwrite output file with the master file after removing specified columns
temp_master=$(mktemp)
remove_columns "$masterFilePath" "$removeColumns" "$delimiter" > "$temp_master"
if [ "$includeLineage" = "true" ]; then
    add_lineage "$temp_master" "master.csv" "$delimiter" > "$outputFile"
else
    mv "$temp_master" "$outputFile"
fi



# Process each source file
for file in $sourceFileFolder/*.csv; do
    if [ -f "$file" ]; then
        temp_source=$(mktemp)
        remove_columns "$file" "$removeColumns" "$delimiter" > "$temp_source"
        if [ "$includeLineage" = "true" ]; then
            sourceFileName=$(basename "$file")
            temp_lineage=$(mktemp)
            add_lineage "$temp_source" "$sourceFileName" "$delimiter" > "$temp_lineage"
            tail -n +2 "$temp_lineage" >> "$outputFile" # Append without header
            rm "$temp_lineage"
        else
            tail -n +2 "$temp_source" >> "$outputFile" # Append without header
        fi
        rm "$temp_source"
    fi
done

echo "Data processing complete. Output file: $outputFile"
