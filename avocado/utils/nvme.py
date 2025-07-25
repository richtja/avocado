# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# This code was inspired in the autotest project,
#
# client/base_utils.py
#
# Copyright: 2022 IBM
# Authors : Naresh Bannoth <nbannoth@linux.vnet.ibm.com>


"""
Nvme utilities
"""


import json
import logging
import os
import re
import time

from avocado.utils import pci, process

LOGGER = logging.getLogger(__name__)


class NvmeException(Exception):
    """
    Base Exception Class for all exceptions
    """


def get_controller_name(pci_addr):
    """
    Returns the controller/Adapter name with the help of pci_address

    :param pci_addr: pci_address of the adapter
    :rtype: string
    :raises: :py:class:`NvmeException` on failure to find pci_address in OS
    """
    if pci_addr in pci.get_pci_addresses():
        path = f"/sys/bus/pci/devices/{pci_addr}/nvme/"
        return "".join(os.listdir(path))
    raise NvmeException("Unable to list as wrong pci_addr")


def get_max_ns_supported(controller_name):
    """
    Returns the number of namespaces supported for the nvme adapter

    :param controller_name: Name of the controller eg: nvme0
    :rtype: integer
    """
    cmd = f"nvme id-ctrl /dev/{controller_name}"
    out = process.run(cmd, ignore_status=True, sudo=True, shell=True).stdout_text
    for line in out.splitlines():
        if line.split(":")[0].strip() == "nn":
            return int(line.split(":")[-1].strip())
    return ""


def get_total_capacity(controller_name):
    """
    Returns the total capacity of the nvme adapter

    :param controller_name: Name of the controller eg: nvme0
    :rtype: integer
    """
    cmd = f"nvme id-ctrl /dev/{controller_name}"
    out = process.run(cmd, ignore_status=True, sudo=True, shell=True).stdout_text
    for line in out.splitlines():
        if line.split(":")[0].strip() == "tnvmcap":
            return int(line.split(":")[-1].strip())
    return ""


def get_controller_id(controll_name):
    """
    Returns the nvme controller id

    :param controller_name: Name of the controller eg: nvme0
    :rtype: string
    """
    cmd = f"nvme id-ctrl /dev/{controll_name}"
    output = process.run(cmd, shell=True, sudo=True, ignore_status=True).stdout_text
    for line in output.splitlines():
        if "cntlid" in line:
            return line.split(":")[-1].strip()
    return ""


def get_current_ns_ids(controller_name):
    """
    Returns the list of namespaces in the nvme controller

    :param controller_name: Name of the nvme controller like nvme0, nvme1
    :rtype: list
    """
    cmd = f"nvme list-ns /dev/{controller_name}"
    namespaces = []
    output = process.run(cmd, shell=True, sudo=True, ignore_status=True).stdout_text
    for line in output.splitlines():
        if line.startswith("["):
            namespaces.append(int(line.split()[1].split("]")[0]) + 1)
    return namespaces


def get_current_ns_list(controller_name, shared_ns=False):
    """
    Returns the list of namespaces in the nvme controller

    :param controller_name: Name of the nvme controller like nvme0, nvme1
    :rtype: list
    """
    namespace_list = []
    namespaces_ids = get_current_ns_ids(controller_name)
    if shared_ns:
        subsys = get_subsystem_using_ctrl_name(controller_name)
        controller_name = f"nvme{subsys[len('nvme-subsy'):]}"
    for ns_id in namespaces_ids:
        namespace_list.append(f"/dev/{controller_name}n{ns_id}")
    return namespace_list


def get_block_size(controller_name, shared_ns=False):
    """
    Returns the block size of the namespace.
    If not found, return defaults to 4k.

    :param namespace: Name of the namespace like /dev/nvme0n1 etc..
    :rtype: Integer
    """
    namespaces = get_current_ns_list(controller_name, shared_ns=shared_ns)
    if namespaces:
        namespace = get_namespace_absolute_path(namespaces[0])
        if shared_ns:
            subsys = get_subsystem_using_ctrl_name(controller_name)
            controller_name = f"nvme{subsys[len('nvme-subsy'):]}"
            ns_match = re.search(r"nvme\d+n(\d+)", namespace)
            if ns_match:
                namespace = f"{controller_name}n{ns_match.group(1)}"
                namespace = get_namespace_absolute_path(namespace)
        cmd = f"nvme id-ns {namespace}"
        out = process.run(cmd, shell=True, ignore_status=True).stdout_text
        for line in out.splitlines():
            if "in use" in line:
                return pow(2, int(line.split()[4].split(":")[-1]))
    return 4096


def get_namespace_absolute_path(namespace):
    """
    Returns absolute path for nvme namespace

    :rtype: String
    """
    if "dev" not in namespace:
        return f"/dev/{namespace}"
    return namespace


def delete_ns(controller_name, ns_id, shared_ns=False):
    """
    Deletes the specified namespace on the controller

    :param controller_name: Nvme controller name to which namespace belongs
    :param ns_id: namespace id to be deleted
    """
    cont_id = get_controller_id(controller_name)
    if shared_ns:
        ctrls = get_alternate_controller_name(controller_name)
        for ctrl in ctrls:
            cont_id = f"{cont_id},{get_controller_id(ctrl)}"
    detach_ns(controller_name, ns_id, cont_id)
    cmd = f"nvme delete-ns /dev/{controller_name} -n {ns_id}"
    if process.system(cmd, shell=True, ignore_status=True):
        raise NvmeException(f"/dev/{controller_name}n{ns_id} delete failed")
    if is_ns_exists(controller_name, ns_id):
        raise NvmeException("namespace still listed even after deleted")


def delete_all_ns(controller_name, shared_ns=False):
    """
    Deletes all the name spaces available on the given nvme controller

    :param controller_name: Nvme controller name eg : nvme0, nvme1 etc..
    """
    namespaces_ids = get_current_ns_ids(controller_name)
    for ns_id in namespaces_ids[::-1]:
        delete_ns(controller_name, ns_id, shared_ns=shared_ns)
        time.sleep(5)


def is_ns_exists(controller_name, ns_id):
    """
    Returns if that particular namespace exists on the controller or not

    :param controller_name: name of the controller on which we want to check
                            ns existence

    :returns: True if exists else False
    :rtype: boolean
    """
    ns_list = get_current_ns_ids(controller_name)
    if ns_id in ns_list:
        return True
    for ctrl in get_alternate_controller_name(controller_name):
        ns_list = get_current_ns_ids(ctrl)
        if ns_id in ns_list:
            return True
    return False


def get_lba(namespace, shared_ns=False):
    """
    Returns LBA of the namespace. If not found, return defaults to 0.

    :param namespace: nvme namespace like /dev/nvme0n1, /dev/nvme0n2 etc..
    :rtype: Integer
    """
    if namespace:
        if shared_ns:
            ns_match = re.search(r"(/dev/)?(nvme\d+)n\d+", namespace)
            if ns_match:
                ctrl_name = ns_match.group(2)
                subsys = get_subsystem_using_ctrl_name(ctrl_name)
                controller_name = f"nvme{subsys[len('nvme-subsy'):]}"
                ns_id_match = re.search(r"nvme\d+n(\d+)", namespace)
                if ns_id_match:
                    namespace = f"{controller_name}n{ns_id_match.group(1)}"
        namespace = get_namespace_absolute_path(namespace)
        cmd = f"nvme id-ns {namespace}"
        out = process.run(cmd, shell=True, ignore_status=True).stdout_text
        for line in out.splitlines():
            if "in use" in line:
                return int(line.split()[1])
    return 0


def ns_rescan(controller_name):
    """
    re-scans all the names spaces on the given controller

    :param controller_name: controller name on which re-scan is applied
    """
    cmd = f"nvme ns-rescan /dev/{controller_name}"
    try:
        process.run(cmd, shell=True, ignore_status=True)
    except process.CmdError as detail:
        LOGGER.debug(detail)


def detach_ns(controller_name, ns_id, cont_id):
    """
    detach the namespace_id to specified controller

    :param ns_id: namespace ID
    :param controller_name: controller name
    :param cont_id: controller_ID
    """
    cmd = f"nvme detach-ns /dev/{controller_name} --namespace-id={ns_id} --controllers={cont_id}"
    if not process.run(cmd, shell=True, ignore_status=True):
        raise NvmeException("detach command failed")
    ns_rescan(controller_name)
    time.sleep(5)
    if is_ns_exists(controller_name, ns_id):
        raise NvmeException("namespace dettached but still listing")


def attach_ns(ns_id, controller_name, cont_id):
    """
    attach the namespace_id to specified controller

    :param ns_id: namespace ID
    :param controller_name: controller name
    :param cont_id: controller_ID
    """
    cmd = f"nvme attach-ns /dev/{controller_name} --namespace-id={ns_id} -controllers={cont_id}"
    if not process.run(cmd, shell=True, ignore_status=True):
        raise NvmeException("namespaces attach command failed")
    ns_rescan(controller_name)
    if not is_ns_exists(controller_name, ns_id):
        raise NvmeException("namespaces attached but not listing")


def create_full_capacity_ns(controller_name, shared_ns=False):
    """
    Creates one namespace with full capacity

    :param controller_name: name of the controller like nvme0/nvme1 etc..
    """
    ns_size = get_total_capacity(controller_name) // get_block_size(controller_name)
    if get_current_ns_list(controller_name, shared_ns=shared_ns):
        raise NvmeException("ns already exist, delete it before creating ")
    create_one_ns("1", controller_name, ns_size, shared_ns=shared_ns)


def create_one_ns(ns_id, controller_name, ns_size, shared_ns=False):
    """
    creates a single namespaces with given size and controller_id

    :param ns_id: Namespace ID
    :param controller_name: name of the controller like nvme0/nvme1 etc..
    :param ns_size: Size of the namespace that is going to be created
    """
    cmd = f"nvme create-ns /dev/{controller_name} --nsze={ns_size} --ncap={ns_size} --flbas=0 --dps=0"
    if shared_ns:
        cmd = f"{cmd} -m 1"
    if process.system(cmd, shell=True, ignore_status=True):
        raise NvmeException(f"namespace create command failed {cmd}")
    cont_id = get_controller_id(controller_name)
    if shared_ns:
        ctrls = get_alternate_controller_name(controller_name)
        for ctrl in ctrls:
            cont_id = f"{cont_id},{get_controller_id(ctrl)}"
    attach_ns(ns_id, controller_name, cont_id)


def create_max_ns(controller_name, force, shared_ns=False):
    """
    Creates maximum number of namespaces, with equal capacity

    :param controller_name: name of the controller like nvme0/nvme1 etc..
    :param force: if wants to create the namespace force, then pass force=True
    """
    if get_current_ns_list(controller_name, shared_ns=shared_ns) and not force:
        raise NvmeException("ns already exist, cannot create max_ns")
    max_ns = int(get_max_ns_supported(controller_name))
    ns_size = get_equal_ns_size(controller_name, max_ns)
    for ns_id in range(1, (max_ns + 1)):
        create_one_ns(str(ns_id), controller_name, ns_size)


def get_equal_ns_size(controller_name, ns_count):
    """
    It calculate and return the size of a namespace when want to create
    more than one namespace with equal sizes

    :param controller_name: name of the controller like nvme0/nvme1 etc...
    :param ns_count: Number of namespaces you want to create with equal sizes
                     it should be less than or equal to max ns supported
                     on the controller
    :rtype: integer
    """
    existing_ns_list = len(get_current_ns_ids(controller_name))
    max_ns = get_max_ns_supported(controller_name)
    if ns_count > (max_ns - existing_ns_list):
        raise NvmeException("required ns count is greater than max supported")
    free_space = get_free_space(controller_name)
    if free_space < 1000:
        raise NvmeException("available free space is less than 1GB")
    return int(((60 * (free_space // 4096)) // 100) // ns_count)


def get_free_space(controller_name):
    """
    Returns the total capacity of the nvme adapter

    :param controller_name: Name of the controller eg: nvme0
    :rtype: integer
    """
    cmd = f"nvme id-ctrl /dev/{controller_name}"
    out = process.run(cmd, ignore_status=True, sudo=True, shell=True).stdout_text
    for line in out.splitlines():
        if line.split(":")[0].strip() == "unvmcap":
            return int(line.split(":")[-1].strip())
    return 0


def create_namespaces(controller_name, ns_count, shared_ns=False):
    """
    creates equal n number of namespaces on the specified controller

    :param controller_name: name of the controller like nvme0
    :param ns_count: number of namespaces to be created
    """
    namespaces = get_current_ns_ids(controller_name)
    if namespaces:
        delete_all_ns(controller_name)
    blk_size = get_total_capacity(controller_name) // get_block_size(controller_name)
    ns_size = blk_size // (ns_count + 1)
    for ns_id in range(1, ns_count + 1):
        create_one_ns(ns_id, controller_name, ns_size, shared_ns=shared_ns)


def get_ns_status(controller_name, ns_id):
    """
    Returns the status of namespaces on the specified controller

    :param controller_name: name of the controller like nvme0
    :param ns_id: ID of namespace for which we need the status

    :rtype: list
    """
    stat = []
    cmd = f"nvme show-topology /dev/{controller_name} -o json"
    data = process.run(cmd, ignore_status=True, sudo=True, shell=True).stdout_text
    json_data = json.loads(data)
    for data in json_data:
        for subsystem in data["Subsystems"]:
            for namespace in subsystem["Namespaces"]:
                nsid = namespace["NSID"]
                for paths in namespace["Paths"]:
                    if nsid == ns_id and paths["Name"] == controller_name:
                        stat.extend([paths["State"], paths["ANAState"]])
    return stat


def get_nslist_with_pci(pci_address):
    """
    Fetches and returns list of namespaces for specified pci_address

    :param pci_address: pci_address of any nvme adapter

    :rtype: list
    """
    ns_list = []
    cmd = "nvme show-topology -o json"
    data = process.run(cmd, ignore_status=True, sudo=True, shell=True).stdout_text
    json_data = json.loads(data)
    for data in json_data:
        for subsystem in data["Subsystems"]:
            for namespace in subsystem["Namespaces"]:
                for paths in namespace["Paths"]:
                    if paths["Address"] == pci_address:
                        ns_list.append(namespace["NSID"])
    return ns_list


def get_nvme_subsystem():
    """
    Fetches subsystem data and returns dictionary of all subsystems

    :rtype: dict
    """
    cmd = "nvme list-subsys -o json"
    data = process.run(cmd, ignore_status=True, sudo=True, shell=True).stdout_text
    json_data = json.loads(data)
    subsystems_dict = {}
    for host in json_data:
        for subsystem in host.get("Subsystems", []):
            nqn = subsystem.get("NQN")
            if nqn:
                subsystem_data = {
                    "Name": subsystem.get("Name"),
                    "IOPolicy": subsystem.get("IOPolicy"),
                    "Type": subsystem.get("Type"),
                    "Paths": subsystem.get("Paths", []),
                }
                subsystems_dict[nqn] = subsystem_data
    return subsystems_dict


def get_controllers_with_nqn(nqn):
    """
    Fetches controllers from subsystem based on input Non-Volatile
    Memory Express Qualified Name

    :rtype: list
    """
    subsys_dict = get_nvme_subsystem().get(nqn)
    if not subsys_dict:
        return ""
    return [path["Name"] for path in subsys_dict["Paths"]]


def get_subsys_name_with_nqn(nqn):
    """
    Fetches subsystem name based on input Non-Volatile Memory Express
    Qualified Name

    :rtype: string
    """
    subsys_dict = get_nvme_subsystem().get(nqn)
    if not subsys_dict:
        return ""
    return subsys_dict["Name"]


def get_controllers_with_subsys(subsys):
    """
    Fetches controllers from nvme subsystem with input as subsystem name

    :rtype: list
    """
    subsys_dict = get_nvme_subsystem()
    subsys_arr = [
        sub_sys_val
        for sub_sys, sub_sys_val in subsys_dict.items()
        if sub_sys_val.get("Name") == subsys
    ]
    if not subsys_arr:
        return []
    return [path["Name"] for path in subsys_arr[0]["Paths"]]


def get_alternate_controller_name(ctrl):
    """
    Fetches other controller in a subsystem based on input controller

    :rtype: list
    """
    subsys_dict = get_nvme_subsystem()
    for device_nqn in subsys_dict:
        ctrls = get_controllers_with_nqn(device_nqn)
        if ctrl in ctrls:
            return ctrls.remove(ctrl) or ctrls
    return []


def get_subsystem_using_ctrl_name(ctrl):
    """
    Fetches subsystem name with controller name as input

    :rtype: string
    """
    subsys_dict = get_nvme_subsystem()
    for device_nqn in subsys_dict:
        ctrls = get_controllers_with_nqn(device_nqn)
        if ctrl in ctrls:
            return get_subsys_name_with_nqn(device_nqn)
    return ""
