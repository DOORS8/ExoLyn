'''
Force the residual F to decrease over two steps
If you want to only solve the equation for xc, rather than xn, you can find the condnewtonold here.
'''
import numpy as np
import parameters as pars
import constants as cnt
import functions as funs
from scipy.integrate import quad
from scipy.optimize import root
import pdb
import sys

def set_rundir(argv):
    """
    the first argument will point to 'relaxation.py'
    """
    i1 = argv[0].rfind('/')
    pars.rdir = argv[0][:i1+1]


def check_input_errors ():

    if pars.xvb.shape[0]!=len(pars.gas):
        print('[init]ERROR:dimensions of >>xvb<< and >>gas<< in parameters.txt are inconsistent!')
        sys.exit()

    if pars.verbose not in ['silent','quiet','default','verbose']:
        print('[init]ERROR:invalid pars.verbose parameter!')
        sys.exit()


def condnewtonold(Parr, reactions, cache, nu, muv, murc, xn):
    '''
    Using Newton-Raphson method to calculate equilibrium concentration
    This is for condensates only, xn is not solved in this method
    '''
    def get_F(n, Sbase, xn, returnjac=False):
        '''get residual function (maybe also Jacobian) of ln(S/bs)'''
        F = np.log(Sbase)
        xvleft = xvb - np.matmul(n, nu)*muv    # a vector with n_v length
        nulogxv = np.sum(nu * np.log(xvleft), axis=1) # a vector with xr length
        xtot = xn + np.sum(n * murc)    # a scalar
        logbs = np.log(n * murc / xtot)    # a scalar with xn length (now xn=xr)
        F = np.log(Sbase) + nulogxv - logbs

        if returnjac==True:
            # calculate Jacobian matrix
            jac1 = -np.matmul(nu, (nu*muv/xvleft).T)
            jac2 = -np.eye(len(n))/n + murc/xtot
            jac = jac1 + jac2

        if returnjac:
            return F, jac
        else:
            return F

    def flag(n):
        ''' check whether the solution is acceptable'''
        xvleft = xvb - np.matmul(n, nu)*muv
        if (n<=0.).any():
            xcflag = False
        else:
            xcflag = True
        if (xvleft<=0.).any():
            xvflag = False
        else:
            xvflag = True
        return xcflag, xvflag

    def newton(Sbase, xn, iniguess):
        ''' Use Newton method to get the supersaturation ratio at one location'''
        while True:    # Reduce initial guess if it is not proper
            xvleft = xvb - np.matmul(iniguess, nu)*muv
            if (xvleft>0).all():
                break
            else:
                iniguess /= 2

        n = iniguess
        F = get_F(n, Sbase, xn)
        while(np.max(np.abs(F))>0.01):
            i = 0
            F, jac = get_F(n, Sbase, xn, returnjac=True)
            step = np.linalg.solve(jac, -F)
            while True:
                xcflag, xvflag = flag(n+step/2**i)
                if xcflag and xvflag:
                    n = n+step/2**i
                    break
                if i>=10:
                    print('error in finding an appropraite solution')
                    pdb.set_trace()
                i=i+1

        return n

    xvb = pars.xvb
    nsolid = np.zeros((len(reactions), len(Parr)))
    Sbase = cache.cachegrid.Sbase_grid
    iniguess = 1e-6*np.ones(len(reactions))
    for i in range(len(Parr)-1):
        result = newton(Sbase[:, i], xn[i], iniguess)
        iniguess = result
        nsolid[:, i] = result
    for i in range(len(Parr)-3, -1, -1):
        result = newton(Sbase[:, i], xn[i], iniguess)
        iniguess = result
        nsolid[:, i] = result

    return nsolid

def condnewton(Parr, reactions, cachegrid, nu, muv, murc, xn0):
    '''
    Using Newton-Raphson method to calculate equilibrium concentration
    '''
    def get_F(n, Sbase, xn, cache, lnSn, returnjac=False):
        '''
        get residual function (maybe also Jacobian) of ln(S/bs)
        the last element is the residual for equation of nuclei ln(Sn*tcoag/xn/rhogas)
        '''
        xvleft = xvb - np.matmul(n, nu)*muv    # a vector with n_v length
        nulogxv = np.sum(nu * np.log(xvleft), axis=1) # a vector with xr length
        xtot = xn + np.sum(n * murc)    # a scalar
        logbs = np.log(n * murc / xtot)    # a scalar with xn length (now xn=xr)
        F = np.log(Sbase) + nulogxv - logbs

        # calculate F (residual) for nuclei
        xc = murc * n
        xcpos = np.maximum(xc, 0)
        ap = funs.cal_ap(xcpos, xn, pars.rho_int)
        n_p = funs.cal_np(xn, cache)
        t_coag = 1/funs.cal_t_coag_inv(ap, pars.rho_int, n_p, cache)
        F = np.append(F, lnSn + np.log(t_coag) - np.log(xn*cache.rho_grid))

        if returnjac:
            # calculate Jacobian matrix
            jac1 = -np.matmul(nu, (nu*muv/xvleft).T)
            jac2 = -np.eye(len(n))/n + murc/xtot
            jac = jac1 + jac2
            # add the last row and column (how change of the xn change the equations) to the Jacobian
            jac = np.hstack((jac, -np.ones((len(n),1))/xtot))
            jac = np.vstack((jac, np.zeros(len(n)+1)))

            # calculate dt_coag/da numerically, then calculate dF[-1]/dn analytically
            t_coag_new = 1/funs.cal_t_coag_inv(ap*1.001, pars.rho_int, n_p, cache)
            dtda = (t_coag_new-t_coag) / (0.001*ap)
            jac[-1, :-1] = 1/t_coag * dtda / (4*np.pi*pars.rho_int*ap**2) * murc * pars.mn0 / xn

            xnnew = xn*1.001
            ap = funs.cal_ap(xcpos, xnnew, pars.rho_int)
            n_p = funs.cal_np(xnnew, cache)
            t_coag_new = 1/funs.cal_t_coag_inv(ap, pars.rho_int, n_p, cache)
            jac[-1, -1] = (np.log(t_coag_new) - np.log(t_coag)) / (0.001*xn) - 1/xn

        if returnjac:
            return F, jac
        else:
            return F

    def flag(n, xn):
        ''' check whether the solution is acceptable'''
        xvleft = xvb - np.matmul(n, nu)*muv
        if (n<=0.).any():
            xcflag = False
        else:
            xcflag = True
        if (xvleft<=0.).any():
            xvflag = False
        else:
            xvflag = True
        if xn<=0.:
            xnflag = False
        else:
            xnflag = True
        return xcflag, xvflag, xnflag

    def newn(step, n, xn):
        ''' From the step and n and xn, find the new n '''
        i = 0
        while(True):
            xcflag, xvflag, xnflag = flag(n+step[:-1]/2**i, xn)
            if xcflag and xvflag:
                n = n+step[:-1]/2**i
                step[-1] = np.minimum(step[-1], xn*9)
                step[-1] = np.maximum(step[-1], -xn*0.9)
                xn += step[-1]
                break
            i = i+1
        return n, xn

    def newton(Sbase, iniguess, cache, lnSn):
        ''' Use Newton method to get the supersaturation ratio at one location'''
        inin = iniguess[:-1]
        inixn = iniguess[-1]
        while True:    # Reduce initial guess if it is not proper
            xvleft = xvb - np.matmul(inin, nu)*muv
            if (xvleft>0).all():
                break
            else:
                inin /= 2    # changed 20230904

        n = inin
        xn = inixn
        F = get_F(n, Sbase, xn, cache, lnSn)
        j = 0
        flagsingle = 0    # flag for the status of finding initial state: 0 for success; -1 for exceed maximum iteration; -2 for step becomes too samll
        Farr = []
        while(np.max(np.abs(F))>0.01):
            # TBD: one way to accelerate is that once n.sum() >> xn, only calculate xn and check whether n.sum() >> xn still satisfies. In this way, less iteration of j may be needed.
            F, jac = get_F(n, Sbase, xn, cache, lnSn, returnjac=True)
            Farr.append(np.max(np.abs(F)))
            step = np.linalg.solve(jac, -F)
            if np.max(np.abs(step/np.append(n, xn)))<1e-13:
                flagsingle = -2
                break
            n, xn = newn(step, n, xn)
            
            # when iterate for too long, break it
            j += 1
            if j>=500:
                flagsingle = -1
                break

        return flagsingle, np.append(n, xn)

    xvb = pars.xvb
    nsolid = np.zeros((len(reactions), len(Parr)))
    xn = np.empty_like(Parr)
    Sbase = cachegrid.Sbase_grid
    lnSn = funs.lnSn(Parr, cachegrid.rho_grid)
    iniguess = 1e-6*np.ones(len(reactions)+1)

    nulogxv = np.sum(nu * np.log(xvb), axis=1) # a vector with xr length
    SR = Sbase * np.atleast_2d(np.exp(nulogxv)).T    # super saturation ratio for cloud base
    status = np.ones_like(Parr) * 100    # save the status of finding initial condition: 0 for success; -1 and -2 for fail; 100 for not done now
    Sfail = np.inf
    clearidx = np.where(SR.sum(axis=0)<1)[0]    # where the atmosphere is clear, without condensation

    # calculate hypothetical xn assuming very less condensation
    ap = np.cbrt(3*pars.mn0/(4*np.pi*pars.rho_int))
    Sn = cachegrid.Sn_grid
    xn_tmp = np.sqrt(pars.mn0 * Sn / funs.cal_t_coag_inv(ap, pars.rho_int, 1, cachegrid)) / cachegrid.rho_grid

    # At this step preserve topidx and bottomidx, which is not as ugly as oversupersat parameter
    # loop over the cloud from upper down and try
    for i in range(len(Parr)):
        # set initial state
        # if last grid point success, use it as initial guess
        if status[i-1]==0:
            iniguess[:-1] = nsolid[:, i-1]
            iniguess[-1] = xn[i-1]
        else:
            iniguess[-1] = xn0[i]
        if i in clearidx and i-1 not in clearidx:
            iniguess[-1] = xn_tmp[i]
            iniguess[:-1] = xn_tmp[i] * SR[:, i] / murc
        if i-1 in clearidx and i not in clearidx:
            iniguess[-1] = xn0[i]

        # solve for the problem
        # if S is too large, skip newton iteration
        # TBD: This is not directly solving the problem, need to think of a way to solve it
        if SR[:, i].sum() < Sfail:
            try:
                flagsingle, result = newton(Sbase[:, i], iniguess, cachegrid[i], lnSn[i])
            except (TypeError, np.linalg.LinAlgError):    # Sometimes the newton method returns error because the matrix is nearly singular.
                flagsingle = -1
        else:
            flagsingle = -1
        status[i] = flagsingle
        if flagsingle == 0:
            nsolid[:, i] = result[:-1]
            xn[i] = result[-1]
        elif flagsingle == -1 and SR[:, i].sum()>10:    # update Sfail if necessary
            Sfail = np.minimum(Sfail, SR[:, i].sum())

    # TBD: When the supersaturation ratio is too high, the code becomes very slow, because it cost ~0.1s for each grid point. Why is that? How to get rid of it?
    # Continue: Maybe could do the similar thing as I did in the main code: control the relative error and absolute error
    # TBD: a more elegant way would be always trying until the status is not upgraded in one loop
    # loop over the cloud from bottom up and try
    # It seems that this step is not necessary
    # for i in range(len(Parr)-2, -1, -1):
    #     # print(i)
    #     # TBD: a more elegant way would be looping over the fail intervals, for each interval, use the closest successful grid poing as iniguess
    #     if status[i]==0:
    #         iniguess[:-1] = nsolid[:, i]
    #         iniguess[-1] = xn[i]
    #         continue
    #     if SR[:, i].sum() < Sfail:
    #         flagsingle, result = newton(Sbase[:, i], iniguess, cachegrid[i], lnSn[i])
    #     else:
    #         flagsingle = -1
    #     status[i] = flagsingle
    #     if flagsingle == 0:
    #         iniguess = result
    #         nsolid[:, i] = result[:-1]
    #         xn[i] = result[-1]
    #     elif flagsingle == -1:
    #         Sfail = np.minimum(Sfail, SR[:, i].sum())

    # insert super saturated values
    if (status<0).any():
        print('[init]WARNING: Failure to find initial guess for some grid points. Extrapolate successful grids')
        failidx = np.where(status<0)[0]
        if failidx[0]==0:
            endi = 0
        else:
            endi = -1
        idx = np.where(np.diff(failidx)!=1)[0]+1    #idx is where the failidx is not continuous
        idx = np.append(idx, len(failidx))
        idx = np.insert(idx, 0, 0)
        for i in range(len(idx)-2, endi, -1):
            nfail = failidx[idx[i+1]-1]-failidx[idx[i]]+1    # number of failed grid points in each sector
            interplever = (np.arange(nfail)+1)/(nfail+1)     # leverage to interpolate the failed points from the neighbouring successful cases
            rightcontrib = np.atleast_2d(nsolid[:, failidx[idx[i+1]-1]+1]).T * interplever
            leftcontrib = np.atleast_2d(nsolid[:, failidx[idx[i]]-1]).T * (1-interplever)
            nsolid[:, failidx[idx[i]:idx[i+1]]] = rightcontrib + leftcontrib
            rightcontrib = xn[failidx[idx[i+1]-1]+1] * interplever
            leftcontrib = xn[failidx[idx[i]]-1] * (1-interplever)
            xn[failidx[idx[i]:idx[i+1]]] = rightcontrib + leftcontrib
        if failidx[0]==0:
            # process the first sector
            nsolid[:, :(failidx[idx[1]-1]+1)] = np.atleast_2d(nsolid[:, failidx[idx[1]-1]+1]).T
            xn[:(failidx[idx[1]-1]+1)] = xn[failidx[idx[1]-1]+1]

    return nsolid, xn

def init(atmosphere, method):
    '''
    Change by now: use atmosphere rather than Parr; don't use cache
    '''
    logP = atmosphere.grid
    Parr = np.exp(logP)
    N = atmosphere.N
    ncod = atmosphere.ncond
    ngas = atmosphere.ngas
    dx = atmosphere.dx
    reactions = atmosphere.chem.reactions

    # prepare chemistry things
    nu = []
    for reaction in reactions:
        nu.append(reaction.gasst)
    nu = np.array(nu)
    muv = atmosphere.chem.mugas
    murc = np.array([atmosphere.chem.molecules[reaction.solid+'(s)'].mu for reaction in reactions])

    y0 = np.zeros((ncod+ngas+1, N))
    # initial concentration without any condensation etc ...
    for i in range(ngas):
        y0[ncod+i] = pars.xvb[i]

    # try to find initial nuclei concentration by eliminating the source term
    def dxndlogP(logP):
        ''' calculate xn derivative to logP '''
        P = np.exp(logP)
        T = funs.TP(P)
        rho = funs.rho(P, T)
        pref = -cnt.kb * T / (pars.g * pars.mgas)
        return - pref * funs.cal_Mn(P)/(pars.Kzz*rho)
    for i in range(N):
        y0[-1, i] = quad(dxndlogP, logP[-1], logP[i], epsabs=1e-12, epsrel=1e-12)[0]
    y0[-1, -1] = y0[-1, -2]**2/y0[-1, -3]    # by definition of the integration, xn would be 0 at the lower boundary. So here interpolate

    # calculate solid concentration 
    if method=='scipy':
        # using scipy to solve the equlibrium concentration of solids
        nsolid = condscipy(Parr, reactions, cache, nu, muv, murc, y0[-1])
    if method=='Newton':
        # My Newton method to calculate the equilibrium concentration of solids.
        nsolid, xn = condnewton(Parr, reactions, atmosphere.cachegrid, nu, muv, murc, y0[-1])
    elif method=='half':
        nsolid = condbis(Parr, reactions, cache, nu, muv)
    elif method=='gold':
        # using minimization method to iterate the equilibrium concentrationof solids
        nsolid = condgold(Parr, reactions, cache, nu, muv, murc, y0[-1])
    else:
        raise Exception('Unknown method to calculate initial solid concentration')

    for i in range(len(reactions)):
        solidindex = reactions[i].solidindex
        y0[solidindex] += atmosphere.chem.molecules[pars.solid[solidindex]+'(s)'].mu * nsolid[i]
        y0[ncod:(ncod+ngas)] -= np.atleast_2d(nu[i]*muv).T*nsolid[i]    # gas concentration -= n*mu

    # post process the gas to be larger than 0. Previous step may introduce numerical error, leading to negative or 0 where it should not.
    for i in range(ngas):
        if (y0[ncod+i]<=0).any():
            ispos = y0[ncod+i]>0
            smallestpos = np.min(y0[ncod+i][ispos])
            y0[ncod+i, ~ispos] = smallestpos

    print('[init]SUCCESS: Find initial condition')

    # If in the future the code do not work, maybe this could save it.
    # is this really necessary? I tested default, Kzz=1e6, T=3000K, T=8000K, this is not needed.
    # for i in range(ngas):
    #     y0[ncod+i] = np.maximum(1e-16, y0[ncod+i])
    # is this really necessary? I tested default, Kzz=1e6, T=3000K, T=8000K, this is not needed.
    # y0[-1] = np.maximum(xn, y0[-1])

    return y0

def findbound(Pa, Pb, N, chem):
    '''
    find an appropriate simulation domain and set up the cache data.
    The initial Pb is, by default, 2 times deeper than the sublimation front
    '''
    def getS(cache):
        '''
        Get the super saturation ratio of all the species.
        '''
        xvb = pars.xvb
        reactions = cache.chem.reactions
        nu = []
        for reaction in reactions:
            nu.append(reaction.gasst)
        nu = np.array(nu)
        nulogxv = np.sum(nu * np.log(xvb), axis=1) # a vector with xr length
        Sbase = cache.cachegrid.Sbase_grid
        SR = Sbase * np.atleast_2d(np.exp(nulogxv)).T    # super saturation ratio for cloud base
        return SR

    Parr = np.logspace(np.log10(Pa), np.log10(Pb), N)
    cache = funs.init_cache(Parr, chem)
    SR = getS(cache)
    if pars.autoboundary:
        while(SR.sum(axis=0)[-1]>1 and cache.cachegrid.T_grid[-1]<=chem.gibbsdata['Tref'][-1]):
            Pb *= 10
            Parr = np.logspace(np.log10(Pa), np.log10(Pb), pars.N)
            cache = funs.init_cache(Parr, chem)
            SR = getS(cache)

        # find the bottom of cloud where everything evaporates
        if np.all(SR.sum(axis=0)<1.):
            # if the super saturation ratio is too low, there will be no cloud
            print('[init.findbound]WARNING: total super saturation ratio smaller than 1 everywhere, the atmosphere is very clean.')
            bottomidx = N-1
        elif np.all(SR.sum(axis=0)>1.):
            print('[init.findbound]WARNING: total super saturation ratio larger than 1 everywhere, may artificially truncate the cloud.')
            bottomidx = N-1
        else:
            bottomidx = np.where((SR.sum(axis=0)[1:]<1) & (SR.sum(axis=0)[:-1]>1))[0][0]+1
        
        # set the final boundary of the atmosphere and initialize cache
        Pb = Parr[bottomidx] * 2
        Parr = np.logspace(np.log10(Pa), np.log10(Pb), pars.N)
        cache = funs.init_cache(Parr, chem)
        if cache.cachegrid.T_grid[-1] > chem.gibbsdata['Tref'][-1]:
            print('[init.findbound]WARNING: No Gibbs energy data given at the highest temperature. Extrapolating the Gibbs energy.')
        SR = getS(cache)

    # check unimportant species whose super saturation ratio is always smaller than 1. User can remove that in the next run to speed up
    for i, reaction in enumerate(cache.chem.reactions):
        if np.all(SR[i]<1.):
            print('[init.findbound]INFO: ' + reaction.solid + ' is an unimportant species with super saturation ratio < 1 everywhere.')
    
    print('[init]SUCCESS: finding domain for the problem.')

    return Parr, cache
