import numpy as np
import pdb
import parameters as pars

def writeatm(y, grid, additional='', fmt1='{:12.4e}'):
    """
    chris: what is the meaning of "additional"?
    Answer: any additional information the user wants to write
    """

    if 'savedir' not in pars.__dict__:
        savedir = './'
    else:
        savedir = pars.savedir

    filename = 'grid' + pars.runname + '.txt'
    print("[output]:writing output to file: "+filename)
    with open(savedir + filename, 'w') as opt:
        # write additional
        opt.write(additional)

        # write the header
        header = '#cols::logP'
        for solidname in pars.solid:
            header += ','
            header += solidname + '(s)'
        for gasname in pars.gas:
            header += ','
            header += gasname
        header += ',nuclei\n'
        opt.write(header)


        # write each row (different pressure layer)
        Nc, Ngrid = y.shape
        fmt2 = (Nc+1)*fmt1+'\n'
        for i in range(len(grid)):
            line = fmt2.format(*((grid[i],)+tuple(y[:,i])))
            opt.write(line)
