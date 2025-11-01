#!/usr/bin/env python3
import csv
from pathlib import Path
import random

OUT = Path(__file__).resolve().parents[1]/'20_QA'/'synthetic_skus.csv'
OUT.parent.mkdir(parents=True, exist_ok=True)

sizes = ['XS','S','M','L','XL']
colors = ['Black','Gray','Blue','Red','Green']

random.seed(42)

with open(OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['SKU','title','brand','gtin','size','color','description','image_link'])
    bad_indices = set(random.sample(range(1,101), 5))  # 5件を意図的に不正
    for i in range(1, 101):
        sku = f'SKU-{i:04d}'
        title = f'Acme Product {i} Waterproof Jacket'
        brand = 'ACME'
        gtin = '4901234567' + f'{i:04d}'  # 12〜14桁相当
        size = random.choice(sizes)
        color = random.choice(colors)
        desc = 'Lightweight waterproof jacket for all seasons.'
        img = f'https://example.com/images/{i}.jpg'
        if i in bad_indices:
            # introduce errors
            if i % 2 == 0:
                size = 'XXL'  # invalid size
            else:
                gtin = '123'  # too short
        w.writerow([sku,title,brand,gtin,size,color,desc,img])

print(f'Wrote {OUT}')






