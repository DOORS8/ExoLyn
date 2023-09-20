# AtmCloud
## Compile the code
After downloading the code, you cancompile the fortran part by running `bash build.sh`

## Run the code
After compilation, you can run the code by `python3 relaxation.py`

## The structure of the code
**parameters.py** will read in and store the parameters.txt file.

**read.py** read in chemical data, i.e. reactions.txt and gibbs.txt.

**init.py** initialize the code, finding appropriate boundary for the code and then finding initial, equilibrium chemical abundances.

**atmosphere_class.py** defines an atmosphere class.

**functions.py** contains the functions to be solved.

**sol.f90** is a file to numerically solve the linear problem. It's much faster than the numpy solver.

**draw.py** draws plots.

## Adding your reactions
1. You can change the reactions in reactions.py. Note that # means comments. 
2. Please also implement gibbs formation energy data for all the molecules involved in the reaction in the gibbs.py. You may find these data in janaf.nist.gov. 
3. The last step is to make sure all the gas and solid species are contained in parameters.txt. The order does not matter.

## Customize parameters
You can change the parameter by modifying parameters.txt. This is a python-like .txt file. You can write down the expressions without calculating yourself. In the expression, calling the parameters you have already defined in previous lines is also allowed.
