import sys
import os
import argparse
import json

def emitGame(infd, outfd):
    HDR = 0
    SAN = 1

    # Assume we start at the start of tags, not somewhere in middle
    # or in a sea of blank lines...
    expect = HDR
    gotOne = False

    n = 0   #  #bytes for a whole game
    
    for data in infd:  # read one PGN line
        outfd.write(data)        

        n = n + len(data)

        # If blank line:  Determine next state:
        if "\n" == data:
            if gotOne:
                if expect == HDR:
                    expect = SAN
                elif expect == SAN:
                    break; # done with SAN; exit for() loop
                gotOne = False
            continue  # keep eating blank lines...

        gotOne = True;

    return n


def error(msg, code=1):
    print("ERROR: %s" % msg)
    sys.exit(1)
    
    
def process(rargs):
    ONE_GAME_SIZE = 800  # Based on casual observations...

    def mkfn(n):
        return "%s.%d.pgn" % (rargs.pathPrefix,n)
    
    if rargs.fname is not None:
        infd = open(rargs.fname, "r")
    else:
        infd = sys.stdin

    fstats = []

    limit = -1
    if rargs.limit:
        limit = rargs.limit

    
    # sizeFiles is always --seq...
    if rargs.sizeFiles is not None:
        totn = 0
        ngames = 0
        tot_ngames = 0                
        n = 0

        # Kickstart on F.0000.pgn:
        fd = open(mkfn(n),"w")

        while True:
            if totn > rargs.sizeFiles:
                fstats.append({"count":ngames})
                n += 1
                totn = 0
                ngames = 0                             
                fd.close()
                fd = open(mkfn(n),"w")

            qq = emitGame(infd, fd)
            if qq == 0:
                break
            totn += qq
            ngames += 1
            tot_ngames += 1                              

            if limit > 0 and tot_ngames >= limit:
                break
            
        # Clean up after last file:
        fstats.append({"count":ngames})            
        fd.close()

    
    elif rargs.numFiles is not None:
        nfiles = rargs.numFiles
    
        if rargs.fname is not None and rargs.seq is not None:
            fstat = os.stat(rargs.fname)
            ngames = int(fstat.st_size / ONE_GAME_SIZE) 
            gpf = int(ngames / nfiles)
        else:
            if rargs.seqCount:
                gpf = int(rargs.seqCount / nfiles)                    
            
        fds = []

        if rargs.seqCount or rargs.seq:
            gcnt = 0
            tot_ngames = 0
            ee = 0

            # Kickstart on F.0000.pgn:
            fd = open(mkfn(ee),"w")
            
            while True:
                if gcnt == gpf and ee < nfiles - 1:
                    fstats.append({"count":gcnt})
                    ee += 1
                    gcnt = 0
                    fd.close()
                    fd = open(mkfn(ee),"w")
                
                qq = emitGame(infd, fd)
                if qq == 0:
                    break
                gcnt += 1
                tot_ngames += 1
            
                if limit > 0 and tot_ngames >= limit:
                    break                

            fstats.append({"count":gcnt})
            fd.close()
            

        else:  # interlace
            ee = 0
            tot_ngames = 0
            
            # Yes, this will open up a bunch of files in advan 
            for n in range(0,nfiles):
                fds.append(open(mkfn(n),"w"))
                fstats.append({"count":0})
                    
            while True:
                if ee == nfiles:
                    ee = 0
                
                qq = emitGame(infd, fds[ee])
                if qq == 0:
                    break

                fstats[ee]['count'] += 1  # !!!
                
                ee += 1

                tot_ngames += 1
            
                if limit > 0 and tot_ngames >= limit:
                    break                                
                
            for n in range(0,len(fds)):
                fds[n].close()

    if True == rargs.stats:
        print(json.dumps({"games":fstats}))

        
def main(argv):
    parser = argparse.ArgumentParser(description=
   """PGN file splitter.

   Read a PGN file and use basic double-CR rules to identify game boundaries
and emit game data into new, smaller files.   By default, given a number of
   output files, pgnsplit will round robin the assignment, leading to usually
   well-balanced distribution but at the "cost" of creating interlaced games.
   Use the seqCount option to force ordering within the files so that the
   original can be reconstituted simply by doing 'cat F.* > zz'.
   
  Designed mostly to address the
database.lichess.org .zst.pgn files which are 30GB zstd compressed and very
difficult to work with and/or perform parallel operations.

Easiest use: split a file into 2 smaller ones:
   pgnsplit.py bigfile.pgn

Split a file into 10 smaller ones:
   pgnsplit.py --numFiles 10 bigfile.pgn


Split a file into n number of smaller ones, each APPROX 1000000 bytes in size:
   pgnsplit.py --sizeFiles 1000000 bigfile.pgn   

   
Get a big .zst.pgn file from lichess.org and cut it up:
   curl -s https://database.lichess.org/standard/lichess_db_standard_rated_2016-05.pgn.zst -o 6X.pgn.zst
       real 0m57.157s
   zstd -d 6X.pgn.zst
       real 0m25.753s
   python3 pgnsplit.py --numFiles 8 6X.pgn
       real 1m17.585s
   Total:  2m39s
   
Fancy!  Slurp giant .pgn.zst file directly into decompressor and make 8 smaller
files.  The lichess.org website posts the number of games in the file.  This
eliminates BOTH the initial zst file and the decompressed big PGN file; you only
need to account for storage for the smaller files:
   curl -s https://database.lichess.org/standard/lichess_db_standard_rated_2016-05.pgn.zst | zstdcat | python3 pgnsplit.py --numFiles 8 --seqCount 6225957
   real	2m45.003s

That file is 1.3GB compressed and 5.7GB uncompressed so 
   5766951106 / 145 secs = ~40MB/sec processing speed

   
   """,
         formatter_class=argparse.ArgumentDefaultsHelpFormatter
   )

    parser.add_argument('--numFiles', 
                        metavar='n',
                        default=2,
                        type=int,
                        help='obvious')

    parser.add_argument('--sizeFiles', 
                        metavar='num_bytes',
                        type=int,
                        help='Create as many output files as needed, starting a new one when the current output file size reaches APPROX num_bytes.  We impose a LOWER limit of 10000 because any smaller than that is suspect.')


    parser.add_argument('--seq',
                        action='store_true',
                        help="""If set, games will fill up each new file in order instead of interlacing.  # games per files is estimated based on filesize; thus, this option CANNOT be used when reading stdin; use --seqCount instead.  If more games are encountered, they will be placed into the last file.""")
    
    parser.add_argument('--seqCount',
                        metavar='n',
                        type=int,
                        help="""If set, this will be used as an estimated
                        count of games and games will fill up each new file in order instead of interlacing.  If more games are encountered, they will be placed into the last file.""")

    parser.add_argument('--limit',
                        metavar='n',
                        type=int,
                        help="""Limit total output of games to n in either numFiles of sizeFiles mode.  Useful for extracting a small number of the first games from the big PGN input.""")
    
    parser.add_argument('--pathPrefix',
                        default='F',
                        metavar='path',                        
                        help='Each output file named <path>.nnnn.pgn.  The prefix can include a directory, e.g /tmp/pgn/FILE. All directories and permissions must be appropriate to be able to open /tmp/pgn/FILE.nnnn.pgn')
    
    parser.add_argument('--stats',
                        action='store_true',
                        help="""Emit collected stats as JSON""")

    parser.add_argument('fname', metavar='PGN file', nargs='?',
                        help='Open this file instead of using stdin')
                        
    rargs = parser.parse_args()

    # Quick checks:
    if rargs.seq and rargs.seqCount:
        error("choose either --seq or --seqCount")

    if rargs.sizeFiles and rargs.sizeFiles < 10000:
        error("--sizeFiles must be >10000")                

    process(rargs)


if __name__ == '__main__':
    main(sys.argv)
