# CSV Merge Script
This script merges records from multiple source CSV files into a master CSV file. It allows for the removal of specified columns, and optionally includes lineage information (date created and source file name) in the output file.

## Author
Syed Bilgrami

## Repository
https://github.com/bilgrami/playground

# Features
- Merge multiple source CSV files into a master CSV file.
- Remove specified columns from the source files before merging.
- Optionally include lineage information (date created and source file name) in the output file.

# Requirements
- Bash shell
- jq (Command-line JSON processor)

# Usage
1) Clone the Repository:

```bash
git clone https://github.com/bilgrami/playground
cd playground
```

2) Prepare param.json:

Create a param.json file with the following structure:

```json
{
  "masterFilePath": "/path/to/master.csv",
  "SourceFileFolderLocation": "/path/to/source/files",
  "SourceFileDelimiter": ",",
  "masterFileColumnsList": ["Date", "Full Name", "Manager ID", "End Date"],
  "sourceFileColumnsList": ["Date", "Employee ID", "First Name", "Last Name", "Full Name", "Manager ID", "End Date"],
  "columnsToRemoveFromSourceFileList": ["First Name", "Last Name"],
  "columnsToAppendFromSourceFile": ["Date", "Full Name", "Manager ID", "End Date"],
  "OutputFileName": "/path/to/output.csv",
  "includeLineage": true or false
}

```

Sample Param File

```json
{
    "masterFilePath": "./data/master.csv",
    "SourceFileFolderLocation": "./data/sources",
    "SourceFileDelimiter": "|",
    "masterFileColumnsList": ["Date", "Full Name", "Manager ID", "End Date"],
    "sourceFileColumnsList": ["Date", "Employee ID", "First Name", "Last Name", "Full Name", "Manager ID", "End Date"],
    "columnsToRemoveFromSourceFileList": ["First Name", "Last Name"],
    "columnsToAppendFromSourceFile": ["Date", "Full Name", "Manager ID", "End Date"],
    "OutputFileName": "./data/output/output.csv",
    "includeLineage": false
  }
  
```

Update the paths and options as needed.

3) Place CSV Files:

Place your master CSV file at the location specified in param.json.
Place your source CSV files in the folder specified in param.json.

4) Run the Script:

Make the script executable and run it:

```bash
chmod +x merge_import_csv.sh
./merge_import_csv.sh ./param.json
```

The script will process the CSV files and create an output.csv file with the combined data.

## Example
Given a master file master.csv and source files a.csv, b.csv, etc., the run.sh script will merge the data from these source files into master.csv, remove the specified columns, and optionally include the lineage information.

# Running tests
```bash
cd test
chmod +x ./test_merge_import.sh
./test_merge_import.sh
```

output 
```
$ ./test_merge_import.sh 
Data processing complete. Output file: ./playground/2024-01-csvImportToMaster/test/output.csv
Running test: Merge files test
Test PASSED
Running test: Remove columns test
Test PASSED
Data processing complete. Output file: ./playground/2024-01-csvImportToMaster/test/output.csv
Running test: Include lineage test
Test PASSED
All tests passed successfully!
```
# License
This project is licensed under the MIT License - see the LICENSE file for details.

