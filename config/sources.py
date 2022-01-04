from os import path
################
# GENERAL DATA #
################
# if you want to sort by multiple primary keys, add to this list
# primary_keys = ['id', 'username']
primary_keys = ['id']

# The path to mapping.csv
mapping_csv_path = path.join(path.abspath(path.curdir), "config", "mapping.csv")

# The path to translations.csv
translations_csv_path = path.join(path.abspath(path.curdir), "config", "translations.csv")

# The path to filtering.csv
filtering_csv_path = path.join(path.abspath(path.curdir), "config", "filtering.csv")

# The location in which to save the resulting csv files
export_csv_path = path.join(path.abspath(path.curdir), "exports")

# Set this to the character that separates each entry in your csv files
csv_delimiter = ","

# if your csv source files have spaces after the delimiters, set this to True
csv_skip_initial_space = True

##################
# PRIMARY SOURCE #
##################
# The name for the first source, used in export file names and fieldnames
source_1_name = "Test 1"

# The path to the first source
source_1_path = path.join(path.abspath(path.curdir), "s1.csv")

######################
# ADDITIONAL SOURCES #
######################
# The name for the second source, used in export file names and fieldnames
source_2_name = "Test 2"

# The path to the second source
source_2_path = path.join(path.abspath(path.curdir), "s2.csv")
