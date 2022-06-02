import csv
import importlib
import json
import os
import sys

import numpy as np

from config import model_groups


def map_number(n, start1, stop1, start2, stop2):
    return ((n - start1) / (stop1 - start1)) * (stop2 - start2) + start2


def create_save_folder(save_folder, sub_folder):
    found = False
    sub_backup = sub_folder
    sf = f"{save_folder}/{sub_folder}"

    i = 1
    while not found:
        if os.path.exists(sf):
            i += 1
            sub_folder = sub_backup + "_v" + str(i)
            sf = f"{save_folder}/{sub_folder}"
        else:
            found = True

    os.makedirs(sf)

    return save_folder, sub_folder


def save_gen_best(save_folder, sub_folder, experiment_name, data):
    with open(f"{save_folder}/{sub_folder}/{experiment_name}_gens_bests.txt", "a") as text_file:
        if data[0] == 0:
            print(f"gen ind fit height", file=text_file)
        genotype = '[' + ','.join(map(lambda x: str(x), np.array(data[1]))) + ']'

        print(f"{data[0]} {genotype} {data[2]} {data[3]}", file=text_file)

    with open(f"{save_folder}/{sub_folder}/{experiment_name}_gens_bests.csv", "a") as csv_file:
        csv_file = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        if data[0] == 0:
            csv_file.writerow(['gen', 'ind', 'fit', 'height'])
        csv_file.writerow([data[0], genotype, data[2], data[3]])


def unpack_models_string(models_string):
    # a messy way to do substiution of aliases. whatever.
    cur_models_string = ""
    next_models_string = models_string
    while cur_models_string != next_models_string:
        cur_models_string = next_models_string
        if not next_models_string.endswith(","):
            next_models_string = next_models_string + ","
        for key in model_groups:
            next_models_string = next_models_string.replace(key, model_groups[key])
        # print("how about ", cur_models_string, "becoming", next_models_string)
    return cur_models_string


def unpack_requested_networks(networks):
    networks = unpack_models_string(networks)
    requested_networks = networks.split(",")
    # remove empty strings
    requested_networks = [x for x in requested_networks if x]
    # remove duplicates and sort
    requested_networks = sorted(list(dict.fromkeys(requested_networks)))
    return requested_networks


def get_model_from_name(k):
    model = load_scoring_object(k)
    return model


def get_active_models_from_arg(networks):
    requested_networks = unpack_requested_networks(networks)
    print("Requested networks: ", requested_networks)
    active_models = {}
    for k in requested_networks:
        if not k.startswith("standard"):
            print("Setting up {}".format(k))
            active_models[k] = get_model_from_name(k)
    if len(active_models) == 0:
        print("_____ WARNING: no active models ______")
    return active_models


def helpful_interface_message_exit(model_interface, e):
    print("==> Failed to load supporting class {}".format(model_interface))
    print("==> Check that package {} is installed".format(model_interface.split(".")[0]))
    print("(exception was: {})".format(e))
    sys.exit(1)


def load_scoring_object(network_name):
    model_class_name = "Scoring"
    model_module_name = network_name
    # print("Loading {} class from {}".format(model_class_name, model_module_name))
    try:
        scoring_class = getattr(importlib.import_module(model_module_name), model_class_name)
    except ImportError:
        try:
            # fallback: try loading from "scoring" subdirectory of library path (todo: default/enforce?)
            # print("isto é meu    "+model_module_name)
            scoring_class = getattr(importlib.import_module("score." + model_module_name), model_class_name)
        except ImportError as e:
            helpful_interface_message_exit(model_module_name, e)
    # print("class loaded.")
    scoring_object = scoring_class()
    return scoring_object


# utilities for mapping imagenet names <-> indexes
def sanatize_label(label):
    label = label.lower()
    label = label.replace("'", "")
    label = label.replace(" ", "_")
    return label


def open_class_mapping(filename="imagenet_class_index.json"):
    class_file = os.path.expanduser(filename)
    with open(class_file) as json_data:
        mapping = json.load(json_data)
    clean_mapping = {}
    for k in mapping:
        v = mapping[k]
        clean_key = int(k)
        clean_mapping[clean_key] = [sanatize_label(v[0]), sanatize_label(v[1])]
    return clean_mapping


def get_map_record_from_key(mapping, key):
    if isinstance(key, int):
        map_index = key
    elif key.isdigit():
        map_index = int(key)
    else:
        map_index = None
        clean_label = sanatize_label(key)
        # first try mapping the label to an index
        for k in mapping:
            if mapping[k][1] == clean_label and map_index is None:
                map_index = k
        if map_index is None:
            # backup try mapping the label to a fullname
            for k in mapping:
                if mapping[k][2] == clean_label and map_index is None:
                    map_index = k
        if map_index is None:
            print("class mapping for {} not found", key)
            return None

    return [map_index, mapping[map_index][0], mapping[map_index][1]]


def get_class_index(mapping, key):
    map_record = get_map_record_from_key(mapping, key)
    if map_record is None:
        return None
    return map_record[0]


def get_class_index_list(mapping, keys):
    key_list = keys.split(",")
    index_list = [get_class_index(mapping, k) for k in key_list]
    return index_list
