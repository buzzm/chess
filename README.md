# chess
All things chess, PGN, BGN, etc.

## pgnsplit.py
pgnsplit.py is a relatively simple util to split large PGN files into smaller
ones.  It relies only on built-in python3 modules.  It was built mostly to be
end-to-end performance dynamic compatible with the download feature of
`database.lichess.org` which vends enormous PGN files in `zstd` compressed
format.  The size/decompression/network speed/lichess data server vending
speed dynamic favors the following use of `pgnsplit`, where the `sizeFiles`
argument can be set to an appropriate comfortable size.  This avoids the
temporary creation of both the `.pgn.zst` file and potentially the
standalone (and massive) decompressed `.pgn` file:
```
  $ time curl -s https://database.lichess.org/standard/lichess_db_standard_rated_2016-05.pgn.zst | zstdcat | python3 pgnsplit.py --sizeFiles 10000000 --seq
  real	2m45.003s
```
For comparison, these are the broken out stage timings (MacBookPro, 16G,
wired inet connection)
```
  $ time curl -s https://database.lichess.org/standard/lichess_db_standard_rated_2016-05.pgn.zst -o 6X.pgn.zst
  real 0m57.157s
  $ stat 6225957.pgn.zst | awk '{print $8}' | commas
  1,357,992,251
  $ time zstd -d 6X.pgn.zst
  real 0m25.753s
  $ stat 6225957.pgn | awk '{print $8}' | commas
  5,766,951,106
  $ time python3 pgnsplit.py --numFiles 8 6X.pgn
  real 1m17.585s
```




