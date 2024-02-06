#!/bin/bash

# Function to run a test
run_test() {
    test_description=$1
    command=$2
    expected=$3

    echo "Running test: $test_description"
    eval $command

    if [[ $? -eq $expected ]]; then
        echo "Test PASSED"
    else
        echo "Test FAILED"
        exit 1
    fi
}

# Test setup: create sample files and param.json
setup() {
    # Create sample master file
    echo "Date,Full Name,Manager ID,End Date" > master.csv

    # Create sample source file
    echo "Date,Employee ID,First Name,Last Name,Full Name,Manager ID,End Date" > source.csv
    echo "2024-01-02,456,Jane,Doe,Jane Doe,123,2024-12-31" >> source.csv

    # Create param.json
    cat <<EOF > param.json
{
  "masterFilePath": "$(pwd)/master.csv",
  "SourceFileFolderLocation": "$(pwd)",
  "SourceFileDelimiter": ",",
  "masterFileColumnsList": ["Date", "Full Name", "Manager ID", "End Date"],
  "sourceFileColumnsList": ["Date", "Employee ID", "First Name", "Last Name", "Full Name", "Manager ID", "End Date"],
  "columnsToRemoveFromSourceFileList": ["First Name", "Last Name"],
  "columnsToAppendFromSourceFile": ["Date", "Full Name", "Manager ID", "End Date"],
  "OutputFileName": "$(pwd)/output.csv",
  "includeLineage": false
}
EOF
}

# Test 1: Verify if the script correctly merges files
test_merge_files() {
    ../merge_import_csv.sh ./param.json
    grep -q "Jane Doe" output.csv
    run_test "Merge files test" "[ $? -eq 0 ]" 0
}

# Test 2: Verify if the script removes specified columns
test_remove_columns() {
    ! grep -q "First Name" output.csv && ! grep -q "Last Name" output.csv
    run_test "Remove columns test" "[ $? -eq 0 ]" 0
}

# Test 3: Verify lineage information inclusion
test_include_lineage() {
    sed -i 's/"includeLineage": false/"includeLineage": true/' param.json
    ../merge_import_csv.sh ./param.json
    grep -q "Date Created,Source File Name" output.csv
    run_test "Include lineage test" "[ $? -eq 0 ]" 0
}

# Run tests
setup
test_merge_files
test_remove_columns
test_include_lineage

echo "All tests passed successfully!"
