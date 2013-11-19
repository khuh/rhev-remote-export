#!/usr/bin/env python
#
# Author : Kyung Huh <khuh@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#

from ovirtsdk.api import API
from ovirtsdk.xml import params
from datetime import datetime
from xml.etree.ElementTree import parse
import time
import os
import re

DESCRIPTION = """
RHEV VM export and import to remote RHEV site.

This script was tested on RHEV 3.2 environments.
To run this scripts it require rhevm-sdk packages provide by Red Hat.

This script is created in order to export VM in local site
then import VM on remote RHEV site automatically.

1. Get informations local and remote RHEV environment.
2. Shutdown VM on local site
3. Export VM on local site
4. Replace VM disk image metadata and ovf data
5. Copy with rsync exported image and data files to remote site
6. Import VM on remote site
7. Start VM on remote site
"""

SRCURL = "https://xxx.xxx.xxx.xxx"
SRCUSERNAME = "admin@internal"
SRCPASSWORD = "password"
SRCCAFILE = "source-ca.pem"
SRCDC = "source_datacenter"
SRCSD = "target_export_storage_domain"
MYVM = "test_vm_name"
RSYNC_SRC = 'root@xxx.xxx.xxx.xxx'

TGTURL = "https://yyy.yyy.yyy.yyy"
TGTUSERNAME = "admin@internal"
TGTPASSWORD = "password"
TGTCAFILE = "target-ca.pem"
TGTDC = "target_datacenter"
TGTSD = "target_export_storage_domain"
TGTDATASD = "target_data_storage_domain"
TGTCLUSTER = "target_cluster"
RSYNC_DST = 'root@yyy.yyy.yyy.yyy'


def conn(url, username, password, ca_file):
    """ define connection RHEV-M api"""
    try:
        api = API(url=url, username=username,
                  password=password,
                  ca_file=ca_file)
        return api
    except Exception as ex:
        print "Unexpected error: %s" % ex


def vm_status(vm):
    """ check initial vm status """
    try:
        vm_status = vm.get_status().state
        print ('vm status : %s') % vm_status
        return vm_status
    except Exception as ex:
        print "Unexpected error: %s" % ex


def now():
    """ print current date and time"""
    now = datetime.today()
    return now


def loop_state():
    """ check current vm status """
    loop_state = vm.get_status().state
    return loop_state


# define vm status sets
vm_status_run_set = set(['up', 'powering_up', 'wait_for_launch',
                         'reboot_in_progress'])
vm_status_wait_set = set(['powering_down', 'image_locked'])

# Print description
print DESCRIPTION

# starting main
print "Backup and Recovery Program started"
print "Start time : %s" % now()
# connect source rhevm api
apisrc = conn(SRCURL, SRCUSERNAME, SRCPASSWORD, SRCCAFILE)
print "Connected to SOURCE %s" % apisrc.get_product_info().name

# select vm for export from config
vm = apisrc.vms.get(MYVM)
vm_name = vm.get_name()
print ('%s %s is selected to export and import.') % (now(), vm_name)

# select source export storage domain
expsd = apisrc.storagedomains.get(name=SRCSD)
expsd_name = expsd.get_name()
source_sd_id = expsd.get_id()
print ('storage domain : %s (%s)') % (expsd_name, source_sd_id)

# select source data center
source_dc = apisrc.datacenters.get(SRCDC)
source_dc_id = source_dc.get_id()
print ('datacenter : %s (%s)') % (source_dc.get_name(), source_dc_id)

if vm_status(vm) in vm_status_run_set:
    print "VM is on of running state"
    print "I will shutdown this VM gracefully"

    try:
        vm.shutdown()
        print "%s Shutting down %s." % (now(), vm.get_name())
        print "I will wait while shutting down."

        #if vm is powering down then wait
        while True:
            vm = apisrc.vms.get(MYVM)
            print ("%s %s status -> %s") % (now(), vm.get_name(), loop_state())
            time.sleep(5)
            if loop_state() == "down":
                print "VM %s is %s. " % (vm.get_name(), loop_state())
                print "I will exit shutdown waiting while loop"
                break
        print ("%s Finished waiting") % now()
        print ("I will export after 5 seconds")
        time.sleep(5)
        # vm exporing start
        try:
            vm = apisrc.vms.get(name=MYVM)
            vm.export(params.Action(storage_domain=expsd,
                      exclusive=True, discard_snapshots=True))
            print "%s Export VM %s has started" % (now(), vm.get_name())
            # waiting while exporting
            while True:
                vm = apisrc.vms.get(name=MYVM)
                print "%s %s status -> %s" % (now(), vm.get_name(), loop_state())
                time.sleep(5)
                if loop_state() == "down":
                    print "VM %s is %s." % (vm.get_name(), loop_state)
                    print "I will exit exporting while loop."
                    break
            print ("Exporting Finished.")
        except Exception as ex:
            print "Unable to export %s : %s " % (vm.get_name(), ex)
    except Exception as ex:
        print "Unable to shutdown %s : %s " % (vm.get_name(), ex)

# vm image locked then quit this program
elif vm_status(vm) in vm_status_wait_set:
    print "VM is controled by something."
    print "You are not allowed to control this vm now."
    print "Please run this program later."

# vm already down then export right now
elif vm_status(vm) == "down":
    # if export image aleary exists then skip export
    vm_list = expsd.vms.list()
    if vm_list:
        for exp_vm in vm_list:
            print "%s (%s)" % (exp_vm.get_name(), exp_vm.get_id())
            if exp_vm.get_name() == vm_name:
                print "%s is already exported." % vm_name
                print "exporting skipped."
    # export vm
    else:
        try:
            vm.export(params.Action(storage_domain=expsd,
                      exclusive=True, discard_snapshots=True))
            print "%s Export VM %s has started" % (now(), vm.get_name())
            # waiting while exporting vm
            while True:
                vm = apisrc.vms.get(name=MYVM)
                print "%s wait %s is %s" % (now(), vm.get_name(), loop_state())
                time.sleep(5)
                if loop_state == "down":
                    print "VM %s is %s" % (vm.get_name(), loop_state)
                    break
            print ("Exporting Finished.")
        except Exception as ex:
            print "Unable to export %s : %s" % (vm.get_name(), ex)
else:
    print "I don't know"

# connect target rhevm api
apitgt = conn(TGTURL, TGTUSERNAME, TGTPASSWORD, TGTCAFILE)
print "Connected to TARGET %s" % apitgt.get_product_info().name

# get target data center uuid
target_dc = apitgt.datacenters.get(TGTDC)
print "Data Center: %s (%s)" % (target_dc.get_name(), target_dc.get_id())
target_dc_id = target_dc.get_id()

# get target storage domain uuid
target_sd = apitgt.storagedomains.get(TGTSD)
print "Storage Domain: %s (%s)" % (target_sd.get_name(), target_sd.get_id())
target_sd_id = target_sd.get_id()

# print datacenter and storage domain info both site source and target
print "=" * 80
print "Source"
print "DC: %s SD: %s " % (source_dc_id, source_sd_id)
print "-" * 80
print "Target"
print "DC: %s SD: %s " % (target_dc_id, target_sd_id)
print "=" * 80

# get export storage domain
expsd = apisrc.storagedomains.get(name=SRCSD)
# get export storage domain path
sdpath = expsd.get_storage().get_path()
# get export storage domain id
sdid = expsd.get_id()

# print storage domian path and id
print "sdpath : %s" % sdpath
print "sdid : %s" % sdid

# get vm on export storage domain
vm = expsd.vms.get(MYVM)
# get vm id
vmid = vm.get_id()

# get ovf file path
ovf_file = sdpath + os.sep + sdid + "/master/vms/" + vmid + os.sep + vmid + ".ovf"
# get ovf directory path
ovf_dir = sdpath + os.sep + sdid + "/master/vms/" + vmid

# print ovf file with full path
print "=== OVF File ==="
print ovf_file

# select meta file on source datacenter
doc = parse(ovf_file)

# get path and id from ovf file
for item in doc.find('References/File').items():
    if item[0] == "{http://schemas.dmtf.org/ovf/envelope/1/}href":
        metahref = item[1]
    if item[0] == "{http://schemas.dmtf.ofg/ovf/envelope/1/}id":
        metaid = item[1]

metahref_dir = re.split(r'/', metahref)
meta_dir = metahref_dir[0]

# get disk image metadata file path
metafile = sdpath + os.sep + sdid + "/images/" + metahref + ".meta"
# get disk image file path
exp_disk_img = sdpath + os.sep + sdid + "/images/" + metahref
# get the directory holding disk image and metadata file
metafile_dir = sdpath + os.sep + sdid + "/images/" + meta_dir

print "=== Metafile dir ==="
print metafile_dir

print "=== VM Image  ==="
print exp_disk_img

print "=== Meta File ==="
print metafile

# get target storage domian path and id
t_sdpath = target_sd.get_storage().get_path()
t_sdid = target_sd.get_id()

# replace meta file with target datacenter uuid
with open(metafile, 'r') as f1:
    data = f1.read()

data_mod = re.sub(sdid, t_sdid, data)

f1.close()

metafile_bak = "/tmp/vm.meta.bak"

with open(metafile_bak, 'w') as f2:
    f2.write(data)

f2.close()

with open(metafile, 'w') as f3:
    f3.write(data_mod)

f3.close()

# replace ovf file with target datacenter uuid and storage domain
source_dc_id = source_dc.get_id()
target_dc_id = target_dc.get_id()

with open(ovf_file, 'r') as f1:
    data = f1.read()

data_replaced = re.sub(sdid, t_sdid, data)
data_replaced = re.sub(source_dc_id, target_dc_id, data_replaced)

f1.close()

ovf_bak = "/tmp/vm.ovf.bak"

with open(ovf_bak, 'w') as f2:
    f2.write(data)
f2.close()

with open(ovf_file, 'w') as f3:
    f3.write(data_replaced)
f3.close()

# send modified export image file
# rsync files disk image, metadata and ovf
dst_ovf = os.path.join(t_sdpath, t_sdid, "master/vms")
dst_images = os.path.join(t_sdpath, t_sdid, "images")

# print destination file paths for ovf and disk images
print "=== dst_ovf    ==="
print dst_ovf
print "=== dst_images ==="
print dst_images

# trasfer files with rsync daemon mode
# rsync daemon is running on target export storage domain machine
os.system("rsync -aPvz %s %s::ovf" % (ovf_dir, RSYNC_DST))
os.system("rsync -aPvz %s %s::images" % (metafile_dir, RSYNC_DST))

# import vm to target datacenter
vm_list = target_sd.vms.list()

print "VMs in export/import storage domain"

# get target data storage domain
data_sd = apitgt.storagedomains.get(TGTDATASD)
# get target cluster
import_cluster = apitgt.clusters.get(TGTCLUSTER)

# print target datacenter vm lists
for vm in vm_list:
    print "%s (%s)" % (vm.get_name(), vm.get_id())

    # import vm
    try:
        vm.import_vm(params.Action(cluster=import_cluster,
                     storage_domain=data_sd, exclusive=True))
        print "%s VM %s importing started" % (now(), vm.get_name())
        print 'from %s Storage Domain' % target_sd.get_name()
        # waiting while exporing vm
        while True:
            vm = apitgt.vms.get(MYVM)
            print "%s  %s is importing status -> %s" % (now(), vm.get_name(), loop_state())
            time.sleep(5)
            if loop_state() == "down":
                print "%s VM %s is %s." % (now(), vm.get_name(), loop_state())
                print "I will exit import while loop"
                break
        print "%s Imported done." % now()

    except Exception as e:
        print 'Failed to import VM: \n%s' % str(e)

    # start vm on target datacenter
    try:
        vm.start()
        print "%s Started '%s'" % (now(), vm.get_name())

    except Exception as ex:
        print "Unable to start '%s': %s" % (vm.get_name(), ex)

# disconnect source datacenter
apisrc.disconnect()
print "Disconnected from SOURCE"

# disconnect target datacenter
apitgt.disconnect()
print "Disconnected from TARGET"

# print script finished
print "Finished at %s" % now()
print "Congratulations!!! Backup and Restore Processes done successfully!!!"
