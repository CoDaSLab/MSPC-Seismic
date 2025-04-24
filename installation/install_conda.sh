cd ./installation/
echo Downloading conda...
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh 

echo Installing conda...
bash Miniconda3-latest-Linux-x86_64.sh -b -p ./miniconda3

echo Deleting residual files...
rm Miniconda3-latest-Linux-x86_64.sh

echo Starting conda...
conda init
source ~/.bashrc
conda --version
echo Updating conda...
conda update conda
conda --version

echo Installation finished!

