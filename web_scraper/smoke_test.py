import sys
sys.path.insert(0, r'C:\Users\Dilip\Desktop\New folder\web scapler')
from schema import StockRecord, AdapterResult, ResolverResult
from normalizer import normalize
from cache import stats

tests = [
    ('Swiggy NSE', 'swiggy'),
    ('COLPAL.NS', 'COLPAL.NS'),
    ('adani enterprises stock', 'adani enterprises'),
    ('  Zomato  ', 'zomato'),
]
all_pass = True
for inp, expected in tests:
    result = normalize(inp)
    ok = result == expected
    all_pass = all_pass and ok
    status = 'OK' if ok else f'FAIL (expected {expected})'
    print(f'  normalize({inp!r}) -> {result!r}  {status}')

print()
print('Cache stats:', stats())
print()
print('Schema imports OK')
print('All normalizer tests passed:', all_pass)
