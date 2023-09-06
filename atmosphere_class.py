'''
The class for an atmosphere
'''
import numpy as np
import parameters as pars
import constants as cnt
import functions as funs

class atmosphere():
    def __init__(self, grid, solid, gas, cache):
        self.grid = grid              # grid
        self.dx = grid[1]-grid[0]     # grid space
        self.N = len(grid)            # number of grid
        self.solid = solid            # list of solid
        self.gas = gas                # list of gas
        self.ncond = len(solid)       # number of solid
        self.ngas = len(gas)          # number of gas
        self.chem = cache.chem    # reactions
        self.y = np.zeros((self.ncond+self.ngas+1, self.N))
        self.cachegrid = cache.cachegrid
        self.cachemid = cache.cachemid
        return

    def update(self, y, do_update_property=True):
        self.y = y
        if do_update_property:
            self.update_property()
        return

    def update_property(self):
        ''' update derived properties of the atmosphere '''
        ncond = self.ncond
        ngas = self.ngas
        y = self.y

        self.xc = np.atleast_2d(y[:ncond])
        self.xv = np.atleast_2d(y[ncond:(ncond+ngas)])
        self.xn = y[-1]
        self.xcpos = np.maximum(self.xc, 0)    # physical (none-negative) xc to be used in certain places
        self.xvpos = np.maximum(self.xv, 0)    # physical (none-negative) xc to be used in certain places
        self.xnpos = np.maximum(self.xn, 0)

        self.ap = funs.cal_ap(self.xcpos, self.xn)    # 20230706: xcpos -> xc
        self.np = funs.cal_np(self.xnpos, self.cachegrid)    # could be <0
        self.bs = self.xcpos / (self.xcpos.sum(axis=0) + self.xn)
        self.v_sed = funs.cal_vsed(self.ap, self.cachegrid)
        self.t_coag_inv = funs.cal_t_coag_inv(self.ap, self.np, self.cachegrid, self.v_sed)

        Sc = np.zeros((len(self.chem.reactions), self.N))
        mugas = np.atleast_2d(self.chem.mugas).T
        for i, reaction in enumerate(self.chem.reactions):
            solidindex = reaction.solidindex
            gasst = reaction.gasst
            Sc[i] = funs.cal_Sc(self.xv, self.ap, self.np, self.bs[solidindex], gasst, solidindex, i, self.cachegrid, mugas, self.chem.musolid)
        self.Sc = Sc
        
        return
