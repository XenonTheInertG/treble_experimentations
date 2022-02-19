#!/usr/bin/python3

from github import Github
from configparser import ConfigParser
import os
import sys
import re
from io import BytesIO

import urllib.request
import zipfile

selfpath = os.path.dirname(sys.argv[0])
config = ConfigParser()
config.read(os.path.join(selfpath, "../release/config.ini"))

g = Github(config['github']['token'])

repo = g.get_user().get_repo("treble_experimentations")

issue = repo.get_issue(int(sys.argv[1]))

comments = [issue.body] + [x.body for x in repo.get_comments() ]

attachments = []
for c in comments:
    matches = re.findall(r'\[([^]]*)\]\(([^)]*)\)', c)
    attachments.extend(m[1] for m in matches)
os.system("rm -Rf tmp*")
apkFiles = []
propFiles = []

fingerprintPrefix = None
brand = None
model = None
density = None

fileId = 0
for attach in attachments:
    print("Checking attachment", attach)
    response = urllib.request.urlopen(attach)
    data = response.read()
    mimeType = response.headers.get_content_type()
    fileId+=1
    if "zip" in mimeType:
        z = zipfile.ZipFile(BytesIO(data))
        for f in z.filelist:
            fileId+=1
            if "prop" in f.filename:
                generated = z.extract(f, path=f'tmp-{fileId}')
                propFiles += [generated]
            if f.filename.endswith("apk"):
                generated = z.extract(f, path=f'tmp-{fileId}')
                apkFiles += [generated]
    elif "prop" in attach:
        fName = f'tmp-{fileId}'
        with open(fName, "wb") as f:
            f.write(data)
        propFiles += [ fName ]

print("Got apks", apkFiles)
print("Got props", propFiles)

for pf in propFiles:
    with open(pf, 'r') as f:
        data = f.read()
        res = re.search('ro.vendor.build.fingerprint(\]: \[|=)([^:\]]*)', data)
        if res is not None:
            fingerprintPrefix = res[2]
        res = re.search('ro.product.vendor.brand(\]: \[|=)([^:\]]*)', data)
        if res is not None:
            brand = res[2]
        res = re.search('ro.vendor.product.brand(\]: \[|=)([^:\]]*)', data)
        if res is not None:
            brand = res[2]
        res = re.search('ro.product.vendor.model(\]: \[|=)([^:\]]*)', data)
        if res is not None:
            model = res[2]
        res = re.search('ro.vendor.product.model(\]: \[|=)([^:\]]*)', data)
        if res is not None:
            model = res[2]
        res = re.search('ro.sf.lcd_density(\]: \[|=)([^:\]]*)', data)
        if res is not None:
            density = res[2]

print(f'Found prefix {fingerprintPrefix}')
print("\t" + str(brand))
print("\t" + str(model))
print("\t" + density)

for apk in apkFiles:
    #Stop at the first apk that succeeds
    cmd = f"brand={brand} model={model} prefix={fingerprintPrefix} bash generate.sh {apk} {propFiles[0]} {density}"
    ret = os.system(cmd)
    if ret == 0:
        break
