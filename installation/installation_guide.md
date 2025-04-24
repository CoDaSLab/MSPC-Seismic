## Installation tutorial
### 1. Open a terminal on the ``/DigiVolCan`` folder
### 2. run ``sh installation/install_conda.sh`` 

This will install conda in your machine. It will create a ``/miniconda3`` folder within the ``/installation`` folder

### 3. run ``sh installation/create_enviroment.sh``. Answer "yes" to any prompts
This will create and setup a conda enviroment called "lafragua" where you can run the software. The files for this enviroment will be located at ``/installation/miniconda3/bin/env/lafragua``

### 4. Close the terminal and open a new one
Conda will not be available until you open a new terminal. You should now see ``(base)`` in the terminal.

### 5. Access the enviroment using ``conda activate lafragua``
This will open the enviroment, where you have all the package installations needed to use the software. Make sure you are using the enviroment before you try to run the software. This is the only step in the isntallation guide that you may need to repeat.