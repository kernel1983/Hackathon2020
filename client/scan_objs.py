
import os
import json


def get_objs(hash, objs):
    d = json.loads(open('data/'+hash).read())
    if d['type'] == 'file':
        objs.update(d['objects'])
    else:
        for i in d['items'].values():
            get_objs(i, objs)
        objs.update(d['items'].values())


all_items = os.listdir('data/')
items = set([i for i in all_items if len(i)==64])
root_folder_items = [i for i in all_items if i.startswith('root_folder')]
print(root_folder_items)

for i in root_folder_items:
    objs = set()
    h = open('data/'+i).read()
    get_objs(h, objs)
    print(len(items - objs))
    for j in (items - objs):
        print(j)
#     items = items - objs

# print(len(items))