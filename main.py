from os import path
import datetime
import csv
from config.sources import *

START_TIME = str(datetime.datetime.now()).replace(':', '-')
LOG_FILE_PATH = path.join(path.abspath(path.curdir), "logs", "log " + START_TIME + ".txt")


def write_to_log(message):
    """
    Writes a message with a timestamp to a log file in the /logs/ directory
    :param message: (str) the message to be recorded
    :return: None
    """
    with open(LOG_FILE_PATH, 'a') as logf:
        time = datetime.datetime.now()
        logf.write(str(time) + " " + message)
        logf.write('\n')


def normalize(x):
    """
    Applies various changes to the given string to make it standardized in format
    Changes applied: make lowercase, remove leading and trailing whitespace
    :param x: (str) the string to be normalized
    :return: the normalized string
    """
    return x.lower().strip()


def make_result_csv(source_name, source_data, csv_type, save_location=export_csv_path):
    """
    Creates a result csv file from a list of dictionary data given to it and saves it to the exports folder
    :param source_name: (str) the name of the source, used to differentiate export file names.
    Must not include characters that are not allowed in file names
    :param source_data: (list) the dictionary data to be converted to csv
    :param csv_type: (str) the type of export, choose between "extra", "missingPK", "duplicate" and "differences"
    :param save_location: (str) the filepath to which the result will be saved
    :return: None, but makes a csv file in the exports folder
    """
    write_to_log(f"writing {csv_type} csv file for {source_name}...")
    time = str(datetime.datetime.now()).replace(':', '-')
    filename = source_name + " " + csv_type + " " + time + ".csv"
    filepath = path.join(save_location, filename)

    with open(filepath, 'w', newline="") as f:
        fieldnames = list(source_data[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        for entry in source_data:
            writer.writerow(entry)


def make_difference_entry(dict_1, dict_2, source_1_name=source_1_name, source_2_name=source_2_name):
    """
    Given two dictionaries with the same keys but different values, creates a difference entry for them
    Assumes both dictionaries have a "primary_key" key
    :param dict_1: (dict) the first dictionary to compare
    :param dict_2: (dict) the second dictionary to compare
    :param source_1_name: (str) the name of source 1, by default the one given in config/sources.py
    :param source_2_name: (str) the name of source 2, by default the one given in config/sources.py
    :return: a dictionary of the form
    {primary_key: val, key1_in_1: val, key1_in_2: val, key2_in_1: val, key2_in_2: val, ...}
    """
    if dict_1["primary_key"] != dict_2["primary_key"]:
        message = "ERROR: Something went wrong when finding entries to take the difference of"
        write_to_log(message)
        raise ValueError(message)

    difference = {"primary_key": dict_1["primary_key"]}
    for key in dict_1.keys():
        if key == "primary_key":
            continue

        difference[f"{key}-[{source_1_name}]"] = dict_1[key]
        try:
            if dict_1[key] == dict_2[key]:
                difference[f"{key}-[{source_2_name}]"] = "*same*"
            else:
                difference[f"{key}-[{source_2_name}]"] = dict_2[key]
        except KeyError:
            message = "ERROR: One of the sources is incorrectly formatted"
            write_to_log(message)
            raise ValueError(message)

    return difference


def make_mapping_dict(mapping_csv_filepath, mode):
    """
    Given a csv file mapping the standard field names to the field names in imported csv files,
    creates a dictionary mapping source names to standard names for every standard/source value pair
    :param mapping_csv_filepath: the filepath to the mapping csv file
    :param mapping: (str) whether this is a translations csv file, or a mapping csv file
    :return: a dictionary of the form {"source_name": "standard_name", ...}
    """
    if mode not in {"mapping", "translations"}:
        message = "ERROR: incorrect mode for make_mapping_dict"
        write_to_log(message)
        raise ValueError(message)

    write_to_log(f"Making {mode} dictionary...")

    mapping_dict = {}

    # Populate the mapping dictionary
    with open(mapping_csv_filepath, 'r') as f:
        reader = csv.reader(f, delimiter=csv_delimiter, skipinitialspace=csv_skip_initial_space)
        headers = next(reader)  # skip the headers
        for line in reader:
            try:
                source_name = line[1]
                standard_name = line[0]
            except IndexError:
                message = f"ERROR: {mode} csv not formatted properly"
                write_to_log(message)
                raise IndexError(message)

            if source_name not in mapping_dict:
                mapping_dict[source_name] = standard_name
            else:
                message = "ERROR: Duplicate source values found in mapping csv"
                write_to_log(message)
                raise IOError(message)

    if mode == "mapping":
        # Ensure all primary keys are mapped
        for key in primary_keys:
            if key not in mapping_dict.values():
                message = "ERROR: Missing a primary key as a standard mapping value in mapping csv"
                write_to_log(message)
                raise IOError(message)

    write_to_log(f"Completed {mode} dictionary")
    return mapping_dict


def make_filtering_list(filtering_csv_filepath=filtering_csv_path):
    """
    Creates a list of tuples that represent what to filter out of results from config/filtering.csv
    :param filtering_csv_filepath: the filepath to the filtering csv file, by default the one given in config/sources.py
    :return: A list of tuples of the form [(fieldname, value), (fieldname, value), ...]
    """
    write_to_log("Making filtering list...")
    filtering_list = []

    with open(filtering_csv_filepath, 'r') as f:
        reader = csv.reader(f, delimiter=csv_delimiter, skipinitialspace=csv_skip_initial_space)
        headers = next(reader)  # skip the headers
        for line in reader:
            try:
                fieldname = line[0]
                value = line[1]
            except IndexError:
                message = "ERROR: filtering csv not formatted properly"
                write_to_log(message)
                raise IndexError(message)
            filtering_list.append((fieldname, value))

    write_to_log("Completed filtering list")
    return filtering_list


def read_source_csv(source_csv_filepath, mapping_dict, translations_dict, filtering_list):
    """
    Creates a python dictionary representation of the given source csv file
    Only includes headers mapped in config/mapping.csv. Standardizes header names.
    :param source_csv_filepath: the filepath to the source csv file
    :param mapping_dict: the mapping dictionary created from the mapping csv file
    :param translations_dict: the translation dictionary created from the translation csv file
    :param filtering_list: the filtering list created from the filtering csv file
    :return: a tuple holding three items:
        source_dict: a dictionary of the form {pk_1: {"standard_name_1": value, ...}, pk_2: {...}}
            where the primary_keys are determined by config/sources.py
        missing_pks: a list of dictionaries of the form [{"standard_name_1": value, ...}, {"standard_name_2": value, ...}]
            representing the entries that are missing pk values
        duplicates: a dictionary of dictionaries of the form {pk_1: [{"standard_name_1": value, ...}, {...}, ...], pk_2: [{...}, {...}, ...]}
            representing the pk's that have duplicate entries

    """
    write_to_log(f"Reading source csv {source_csv_filepath}...")
    entries = []
    missing_pks = []
    duplicates = []
    seen_pks = set()
    headers_to_compare = []
    pk_indices = []

    with open(source_csv_filepath, 'r') as f:
        reader = csv.reader(f, delimiter=csv_delimiter, skipinitialspace=csv_skip_initial_space)

        # build the list of headers that we care about
        headers = next(reader)
        # Find where the primary key is in the headers
        for idx, header in enumerate(headers):
            if header in mapping_dict:
                if mapping_dict[header] in primary_keys:  # skip the primary keys
                    pk_indices.append(idx)
                    continue
                headers[idx] = mapping_dict[header]
                headers_to_compare.append((header, idx))

        # build the source list
        write_to_log("Populating intermediate structures...")
        for entry in reader:
            entry_dict = {}

            # build the primary key
            pk = ""
            for pk_idx in pk_indices:
                pk = pk + entry[pk_idx] + " "
            entry_dict["primary_key"] = normalize(pk)

            for item in headers_to_compare:
                header = item[0]
                header_idx = item[1]
                value = entry[header_idx]
                if value in translations_dict:
                    entry_dict[headers[header_idx]] = normalize(translations_dict[value])
                else:
                    entry_dict[headers[header_idx]] = normalize(value)

            # Decide whether to filter this entry out of the final results
            ignore = False
            for item in filtering_list:
                fieldname = item[0]
                value = item[1]
                if entry_dict[fieldname] == value:
                    ignore = True
            if ignore:
                continue

            # populate the entry list
            if pk == "" or pk.isspace():  # if the entry is missing values for all primary keys
                missing_pks.append(entry_dict)
            else:
                pk = normalize(pk)
                if pk in seen_pks:  # catch duplicate entries
                    duplicates.append(entry_dict)

                    if pk in {x['primary_key'] for x in entries}:
                        to_delete = [x for x in entries if x['primary_key'] == pk]
                        if len(to_delete) == 1:  # There should only be one item with the above property
                            item_to_delete = to_delete[0]
                            duplicates.append(item_to_delete)
                            entries.remove(item_to_delete)
                        else:
                            message = "Something went wrong with the formatting of this source"
                            write_to_log(message)
                            raise IndexError(message)
                else:
                    seen_pks.add(pk)
                    entries.append(entry_dict)

    # sort results alphabetically by primary key
    entries.sort(key=lambda x: x['primary_key'])
    duplicates.sort(key=lambda x: x['primary_key'])

    write_to_log(f"Completed reading {source_csv_filepath}")
    return entries, missing_pks, duplicates


def compare_sources(source_1_name=source_1_name, source_2_name=source_2_name,
                    source_1_filepath=source_1_path, source_2_filepath=source_2_path,
                    mapping_csv_filepath=mapping_csv_path,
                    translations_csv_filepath=translations_csv_path,
                    filtering_csv_filepath=filtering_csv_path):
    """
    Given two csv source files, compares the two of them based on a set of important fields defined in config/mapping.csv
    calling this method with no arguments will run it on the files given in config/sources.py by default
    :param source_1_name: (str) the name of the first source, by default the one defined in config/sources.py
    :param source_2_name: (str) the name of the second source, by default the one defined in config/sources.py
    :param source_1_filepath: the filepath to the first source, by default the one defined in config/sources.py
    :param source_2_filepath: the filepath to the second source, by default the one defined in config/sources.py
    :param mapping_csv_filepath: the filepath to the mapping csv file, by default the one provided by config/mapping.csv
    :param translations_csv_filepath: the filepath to the translations csv file, by default the one provided by config/translations.csv
    :param filtering_csv_filepath: the filepath to the filtering csv file, by default the one provided by config/filtering.csv
    :return: None, but creates various csv files as it analyzes the two sources.
    If a csv result would be empty, it does not get created
        source_1_extra: all of the entries present in source 1 that are not present in source 2
        source_2_extra: all of the entries present in source 2 that are not present in source 1
        source_1_missingPK: all of the entries in source 1 that are missing values for the primary key
        source_2_missingPK: all of the entries in source 2 that are missing values for the primary key
        source_1_duplicate: all of the duplicate entries in source 1
        source_2_duplicate: all of the duplicate entries in source 1
        differences: all of the differences found between source 1 and source 2
    """
    write_to_log(f"Reading {source_1_name} and {source_2_name}...")
    mapping_dict = make_mapping_dict(mapping_csv_filepath, mode="mapping")
    translations_dict = make_mapping_dict(translations_csv_filepath, mode="translations")
    filtering_list = make_filtering_list(filtering_csv_filepath)
    source_1_entries, source_1_missingPK, source_1_duplicates = \
        read_source_csv(source_1_filepath, mapping_dict, translations_dict, filtering_list)
    source_2_entries, source_2_missingPK, source_2_duplicates = \
        read_source_csv(source_2_filepath, mapping_dict, translations_dict, filtering_list)
    source_1_extra = []
    source_2_extra = []
    differences = []

    source_1_entries_copy = [x.copy() for x in source_1_entries]
    source_2_entries_copy = [x.copy() for x in source_2_entries]

    write_to_log(f"Comparing {source_1_name} and {source_2_name}...")
    for entry in source_1_entries_copy:
        entry_pk = entry['primary_key']
        matches = [x for x in source_2_entries_copy if x['primary_key'] == entry_pk]
        if len(matches) > 1:
            write_to_log("ERROR: Something went wrong when searching for duplicates")
        elif len(matches) == 0:  # the entry is missing from source 2
            source_1_extra.append(entry)
        else:  # the entry exists in both
            match = matches[0]
            if entry != match:
                differences.append(make_difference_entry(entry, match))

            source_1_entries.remove(entry)
            source_2_entries.remove(match)

    # now, every entry left in source_2_entries is extra to source 2
    source_2_extra.extend(source_2_entries)

    write_to_log("Creating csv files...")
    # Create "missingPK" csv files if the missingPK lists are populated
    if len(source_1_missingPK) > 0:
        make_result_csv(source_1_name, source_1_missingPK, "missingPK")
    if len(source_2_missingPK) > 0:
        make_result_csv(source_2_name, source_2_missingPK, "missingPK")

    # Create "duplicates" csv files if the duplicates lists are populated
    if len(source_1_duplicates) > 0:
        make_result_csv(source_1_name, source_1_duplicates, "duplicates")
    if len(source_2_duplicates) > 0:
        make_result_csv(source_2_name, source_2_duplicates, "duplicates")

    # make the "extra" csv files if the extra lists are populated
    if len(source_1_extra) > 0:
        make_result_csv(source_1_name, source_1_extra, "extra")
    if len(source_2_extra) > 0:
        make_result_csv(source_2_name, source_2_extra, "extra")

    # make the "differences" csv file if the differences list is populated
    if len(differences) > 0:
        name = source_1_name + " " + source_2_name
        make_result_csv(name, differences, "differences")

    write_to_log("Comparison complete!")


if __name__ == '__main__':
    compare_sources()

    #Testing particular methods as I was developing
    #print(make_mapping_dict(mapping_csv_path))
    # source, missingpk, duplicates = read_source_csv(source_1_path)
    # for el in source:
    #     print(el)
    # print()
    # # for el in missingpk:
    # #     print(el)
    # print(missingpk)
    # print()
    # for el in duplicates:
    #     print(el)
    #
    # make_result_csv(source_1_name, source, "source")
    # d1 = {"primary_key": 100, "first_name": "Jane", "last_name": "Doe", "middle_name": ""}
    # d2 = {"primary_key": 100, "first_name": "Janet", "last_name": "Doe", "middle_name": ""}
    # print(make_difference_entry(d1, d2))

    # thing = [{"primary_key": 100, "school": "MIT"}, {"primary_key": 101, "school": "Harvard"}, {"primary_key": 102, "school": "MIT"}]
    # thing = [x for x in thing if x["school"] != "Harvard"]
    # print(thing)
