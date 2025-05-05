# Installation tutorial

## Python environment

### 1. Open a terminal on the ``/DigiVolCan`` folder
### 2. run ``sh installation/install_conda.sh`` 

This will install conda in your machine. It will create a ``/miniconda3`` folder within the ``/installation`` folder

### 3. run ``sh installation/create_enviroment.sh``. Answer "yes" to any prompts
This will create and setup a conda enviroment called "lafragua" where you can run the software. The files for this enviroment will be located at ``/installation/miniconda3/bin/env/lafragua``

### 4. Close the terminal and open a new one
Conda will not be available until you open a new terminal. You should now see ``(base)`` in the terminal.

### 5. Access the enviroment using ``conda activate lafragua``
This will open the enviroment, where you have all the package installations needed to use the software. Make sure you are using the enviroment before you try to run the software. This is the only step in the isntallation guide that you may need to repeat.


## MATLAB

This tutorial explains how to install MATLAB on a remote server. This only works for **version R2020b or lower**.

You need a **MATLAB license** to install it.

### 1. Go to <https://mathworks.com/downloads/> on your computer and log into your account.

### 2. Select the version of MATLAB you want and download it. Make sure you choose the correct OS.

### 3. Upload the compressed installation files to the `/installation/MATLAB` folder. Create the `MATLAB` folder first if it doesn't exist.

### 4. Open a terminal on the `/installation/MATLAB` folder. 

### 5. Unzip the compressed files by running `unzip matlab_R20XXx_glnxa64 -d matlab_R20XXx_glnxa64` (change the version name to the one you downloaded).

The `matlab_R20XXx_glnxa64` file name depends on the MATLAB version, so make sure to write it correctly in every step.

### 6. Run `chmod -R u+rwx matlab_R20XXx_glnxa64`.

This gives your user permission to write and execute any files inside the directory.

### 6. Run `matlab_R20XXx_glnxa64/bin/glnxa64/install_unix_legacy` (change the version name to the one you downloaded).

A new window will open with instructions on how to install MATLAB.

### 7. Follow the installer instructions to activate your license on the server. When asked for the installation path, write `/home/<user>/DigiVolcan/installation/MATLAB/R20XXx`.

You do not need to enter an installation key.

### 8. Keep following the instructions and install MATLAB.

### 9. Once it is installed, run `R20XXx/bin/matlab`. This will open MATLAB.

You should see MATLAB's graphic user interface.

### 10. Remove the installer by running `rm -r matlab_R20XXx_glnxa64` and `rm matlab_R20XXx_glnxa64.zip`.
