#!/usr/bin/env python3
import pathlib
d = pathlib.Path('/Users/lucas.liang/Desktop/Sylph/Carror_OS/.omc/state')
f = d / 'current-scope.txt'
f.write_text('')
print(f'Created {f}')
